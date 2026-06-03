from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import numpy as np

from app.algorithms.process_c import compute_process_c
from app.algorithms.process_s import compute_process_s
from app.core.config import settings

A_C = settings.A_C  # 0.1333


@dataclass
class EnergyZone:
    zone_type: str  # "wake", "morning_peak", "afternoon_dip", "evening_peak", "melatonin_window"
    start_minute: int
    end_minute: int


@dataclass
class NudgeEvent:
    minute: int
    message: str
    nudge_type: str
    priority: int = 3  # 1-5, 5 = highest priority


@dataclass
class EnergySchedule:
    energy_values: np.ndarray  # 1440 points (1 per minute for 24h)
    zones: list[EnergyZone]
    nudges: list[NudgeEvent]
    wake_time: datetime
    energy_potential_score: float  # 0-100, higher = more peak energy available


def compute_energy_schedule(
    wake_time: datetime,
    h_at_wake: float,
    phi: float,
    sleep_debt_mins: float = 0.0,
    snop_hours: float = 8.0,
    enabled_habit_ids: set[str] | None = None,
) -> EnergySchedule:
    """Compute 24-hour energy schedule from wake time.

    Phi(t) = H(t) - A_c * C(t)

    Args:
        wake_time: datetime of user's wake up
        h_at_wake: Process S value at wake time
        phi: circadian phase
        sleep_debt_mins: current cumulative sleep debt in minutes
        snop_hours: user's personalized SNOP in hours
        enabled_habit_ids: set of enabled habit IDs (None = all enabled)

    Returns:
        EnergySchedule with 1440 energy points, zones, and nudges
    """
    # 1440 minutes in a day, 5-minute resolution = 288 points
    n_points = 288
    t_hours = np.linspace(0.0, 24.0, n_points, endpoint=False)

    # All awake (Process S rises from h_at_wake)
    sleep_mask = np.zeros(n_points, dtype=bool)

    h = compute_process_s(t_hours, sleep_mask, h_initial=h_at_wake)
    c = compute_process_c(t_hours, phi=phi)
    energy = h - A_C * c

    # Normalize to [0, 100] scale
    energy_normalized = _normalize_energy(energy)

    # Classify zones — pass C(k) for dynamic melatonin window
    zones = _classify_zones(energy_normalized, t_hours, c)

    # Generate nudges with adaptive prioritization
    nudges = _generate_nudges(zones, wake_time, sleep_debt_mins, snop_hours, enabled_habit_ids)

    # Energy Potential Score: how much peak energy capacity remains
    potential = _compute_energy_potential(h_at_wake)

    return EnergySchedule(
        energy_values=energy_normalized,
        zones=zones,
        nudges=nudges,
        wake_time=wake_time,
        energy_potential_score=potential,
    )


def _normalize_energy(energy: np.ndarray) -> np.ndarray:
    """Normalize energy values to 0-100 scale."""
    min_val, max_val = energy.min(), energy.max()
    if max_val - min_val == 0:
        return np.full_like(energy, 50.0)
    return (energy - min_val) / (max_val - min_val) * 100.0


def _compute_energy_potential(h_at_wake: float) -> float:
    """Compute Energy Potential Score (0-100).

    From research.md §1.3: high sleep debt pushes H(t) baseline upward,
    narrowing the gap between H(t) and C(k). This reduces peak amplitude
    and deepens the afternoon dip — explaining chronic exhaustion.

    Score = (1 - h_at_wake) * 100

    Where h_at_wake = sleep_debt / SNOP (clamped to [0, 1]):
    - 0 debt → h_at_wake=0 → score=100 (full potential)
    - max debt → h_at_wake=1 → score=0 (no energy capacity left)
    """
    potential = (1.0 - h_at_wake) * 100.0
    return float(np.clip(potential, 0.0, 100.0))


def _classify_zones(
    energy: np.ndarray,
    t_hours: np.ndarray,
    c_values: np.ndarray,
) -> list[EnergyZone]:
    """Classify time periods into physiological zones based on energy curve.

    Args:
        energy: normalized energy values [0-100]
        t_hours: time points in hours
        c_values: Process C circadian signal (used for melatonin window)
    """
    zones = []

    # Find local maxima and minima
    peaks = _find_peaks(energy)
    troughs = _find_peaks(-energy)

    # Wake zone: first 90 minutes (sleep inertia)
    zones.append(EnergyZone("wake", 0, 90))

    # Morning peak: highest peak in first 8 hours
    morning_peaks = [p for p in peaks if 90 < t_hours[p] * 60 < 480]
    if morning_peaks:
        best = max(morning_peaks, key=lambda p: energy[p])
        start = max(0, best - 30)
        end = min(len(energy), best + 30)
        zones.append(EnergyZone("morning_peak", start, end))

    # Afternoon dip: lowest trough between hours 5-9
    afternoon_troughs = [t for t in troughs if 300 < t_hours[t] * 60 < 540]
    if afternoon_troughs:
        worst = min(afternoon_troughs, key=lambda t: energy[t])
        start = max(0, worst - 60)
        end = min(len(energy), worst + 60)
        zones.append(EnergyZone("afternoon_dip", start, end))

    # Evening peak: second highest peak in hours 10-16
    evening_peaks = [p for p in peaks if 600 < t_hours[p] * 60 < 960]
    if evening_peaks:
        best = max(evening_peaks, key=lambda p: energy[p])
        start = max(0, best - 30)
        end = min(len(energy), best + 30)
        zones.append(EnergyZone("evening_peak", start, end))

    # Melatonin window (DLMO): dynamically computed from circadian phase
    melatonin_start, melatonin_end = _compute_melatonin_window(c_values, t_hours)
    zones.append(EnergyZone("melatonin_window", melatonin_start, melatonin_end))

    return zones


def _compute_melatonin_window(
    c_values: np.ndarray,
    t_hours: np.ndarray,
) -> tuple[int, int]:
    """Compute melatonin window from Process C circadian signal.

    DLMO (Dim Light Melatonin Onset) occurs when the circadian drive
    begins declining in the evening, typically 2-3h before habitual sleep onset.

    Strategy: find the nadir (minimum) of C(k) — this corresponds to the
    core body temperature minimum, which occurs ~2h before habitual wake time.
    The melatonin window opens ~5h before the nadir and closes ~3h before.

    For a typical Early Bird (nadir ~3 AM):  window ~10 PM–12 AM
    For a typical Night Owl  (nadir ~5 AM):  window ~12 AM–2 AM
    """
    # Find the nadir (minimum) of C(k) across the full 24h cycle
    nadir_idx = int(np.argmin(c_values))
    nadir_hour = t_hours[nadir_idx]

    # Convert to 1-indexed minute count for zone boundaries
    nadir_minute = int(nadir_hour * 60)

    # Melatonin window: opens 5h before nadir (DLMO), closes 3h before nadir
    # This gives a ~2h window centered around DLMO
    start_minute = nadir_minute - 300  # 5 hours before nadir
    end_minute = nadir_minute - 180    # 3 hours before nadir

    # Wrap around if before midnight (e.g., nadir at 3 AM → start at 22:00)
    # For zones, we keep minutes relative to wake time (0-1440 range)
    # If the window falls before midnight (negative), shift into valid range
    if start_minute < 0:
        start_minute += 1440
    if end_minute < 0:
        end_minute += 1440

    return start_minute, end_minute


def _find_peaks(data: np.ndarray) -> list[int]:
    """Simple peak finding using first derivative sign change."""
    peaks = []
    for i in range(1, len(data) - 1):
        if data[i] > data[i - 1] and data[i] > data[i + 1]:
            peaks.append(i)
    return peaks


def _generate_nudges(
    zones: list[EnergyZone],
    wake_time: datetime,
    sleep_debt_mins: float = 0.0,
    snop_hours: float = 8.0,
    enabled_habit_ids: set[str] | None = None,
) -> list[NudgeEvent]:
    """Generate science-based nudge events mapped to circadian phases.

    16 nudges derived from sleep science research, each timed to the
    user's personalized energy zones rather than fixed clock times.
    Nudges are adaptively prioritized based on sleep debt level and
    filtered by user preferences.

    Args:
        zones: classified energy zones
        wake_time: user's wake up time
        sleep_debt_mins: current cumulative sleep debt in minutes
        snop_hours: user's personalized SNOP in hours
        enabled_habit_ids: set of enabled habit IDs (None = all enabled)
    """
    from app.services.habit_adaptation import adapt_nudge_priorities

    raw_nudges = []

    # Index zones by type for quick lookup
    zone_map = {z.zone_type: z for z in zones}

    wake_zone = zone_map.get("wake")
    morning_peak = zone_map.get("morning_peak")
    afternoon_dip = zone_map.get("afternoon_dip")
    evening_peak = zone_map.get("evening_peak")
    melatonin = zone_map.get("melatonin_window")

    # ── Wake Zone nudges (0-90 min after waking) ──────────────────────
    if wake_zone:
        raw_nudges.append({"minute": wake_zone.start_minute, "message": "Get 10-15 min of bright natural light to clear sleep inertia and reset your circadian clock", "nudge_type": "light_exposure"})
        raw_nudges.append({"minute": wake_zone.start_minute + 10, "message": "Drink a full glass of water — your body is dehydrated after sleep", "nudge_type": "morning_hydration"})
        raw_nudges.append({"minute": wake_zone.start_minute + 20, "message": "Do 5 min of light stretching to activate your body and improve circulation", "nudge_type": "morning_stretch"})

    # ── Morning Peak nudges (highest cognitive performance) ────────────
    if morning_peak:
        raw_nudges.append({"minute": morning_peak.start_minute, "message": "Peak alertness window — schedule your most important deep work now", "nudge_type": "deep_work"})
        raw_nudges.append({"minute": morning_peak.start_minute + 30, "message": "Best time for exercise — physical activity now boosts alertness and mood for hours", "nudge_type": "morning_exercise"})
        raw_nudges.append({"minute": morning_peak.start_minute + 60, "message": "Ideal window for caffeine — pair with your natural cortisol peak for maximum effect", "nudge_type": "strategic_caffeine"})

    # ── Midday transition ──────────────────────────────────────────────
    if melatonin:
        caffeine_cutoff = melatonin.start_minute - 600
        if caffeine_cutoff > 0:
            raw_nudges.append({"minute": caffeine_cutoff, "message": "Caffeine cutoff — stop all caffeine now to protect tonight's sleep quality", "nudge_type": "caffeine_cutoff"})

        meal_cutoff = melatonin.start_minute - 180
        if meal_cutoff > 0:
            raw_nudges.append({"minute": meal_cutoff, "message": "Finish any heavy meals now — digestion too close to bed disrupts sleep", "nudge_type": "meal_timing"})

        hydration_taper = melatonin.start_minute - 120
        if hydration_taper > 0:
            raw_nudges.append({"minute": hydration_taper, "message": "Start tapering fluid intake to avoid nighttime bathroom trips", "nudge_type": "hydration_taper"})

    # ── Afternoon Dip nudges (natural energy low) ─────────────────────
    if afternoon_dip:
        raw_nudges.append({"minute": afternoon_dip.start_minute, "message": "Energy dip detected — a 20-min power nap now can reduce sleep debt without grogginess", "nudge_type": "power_nap"})
        raw_nudges.append({"minute": afternoon_dip.start_minute + 15, "message": "Low energy window — switch to routine tasks, emails, or light meetings", "nudge_type": "passive_tasks"})
        raw_nudges.append({"minute": afternoon_dip.start_minute + 30, "message": "A short walk outside can boost alertness during the afternoon dip", "nudge_type": "afternoon_walk"})

    # ── Evening Peak nudges (second energy rise) ──────────────────────
    if evening_peak:
        raw_nudges.append({"minute": evening_peak.start_minute, "message": "Last window for moderate exercise — intense activity later will delay sleep", "nudge_type": "evening_exercise"})
        raw_nudges.append({"minute": evening_peak.start_minute + 30, "message": "Good window for social activities, creative work, or planning tomorrow", "nudge_type": "social_creative"})

    # ── Wind Down & Melatonin Window nudges ───────────────────────────
    if melatonin:
        raw_nudges.append({"minute": melatonin.start_minute - 30, "message": "Start reducing blue light — enable night mode, dim screens to protect melatonin", "nudge_type": "blue_light"})
        raw_nudges.append({"minute": melatonin.start_minute, "message": "Melatonin production starting — begin your wind down: light reading, breathing exercises, no screens", "nudge_type": "wind_down"})

    # Adapt priorities based on sleep debt
    prioritized = adapt_nudge_priorities(raw_nudges, sleep_debt_mins, snop_hours)

    # Filter by user preferences
    if enabled_habit_ids is not None:
        prioritized = [n for n in prioritized if n["nudge_type"] in enabled_habit_ids]

    # Convert to NudgeEvent objects
    nudges = [
        NudgeEvent(
            minute=n["minute"],
            message=n["message"],
            nudge_type=n["nudge_type"],
            priority=n["priority"],
        )
        for n in prioritized
    ]

    return nudges
