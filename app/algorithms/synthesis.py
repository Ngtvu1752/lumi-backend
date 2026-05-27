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


@dataclass
class EnergySchedule:
    energy_values: np.ndarray  # 1440 points (1 per minute for 24h)
    zones: list[EnergyZone]
    nudges: list[NudgeEvent]
    wake_time: datetime


def compute_energy_schedule(
    wake_time: datetime,
    h_at_wake: float,
    phi: float,
) -> EnergySchedule:
    """Compute 24-hour energy schedule from wake time.

    Phi(t) = H(t) - A_c * C(t)

    Args:
        wake_time: datetime of user's wake up
        h_at_wake: Process S value at wake time
        phi: circadian phase

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

    # Classify zones
    zones = _classify_zones(energy_normalized, t_hours)

    # Generate nudges
    nudges = _generate_nudges(zones, wake_time)

    return EnergySchedule(
        energy_values=energy_normalized,
        zones=zones,
        nudges=nudges,
        wake_time=wake_time,
    )


def _normalize_energy(energy: np.ndarray) -> np.ndarray:
    """Normalize energy values to 0-100 scale."""
    min_val, max_val = energy.min(), energy.max()
    if max_val - min_val == 0:
        return np.full_like(energy, 50.0)
    return (energy - min_val) / (max_val - min_val) * 100.0


def _classify_zones(energy: np.ndarray, t_hours: np.ndarray) -> list[EnergyZone]:
    """Classify time periods into physiological zones based on energy curve."""
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

    # Melatonin window: 2-3h before end of day
    zones.append(EnergyZone("melatonin_window", 1260, 1380))

    return zones


def _find_peaks(data: np.ndarray) -> list[int]:
    """Simple peak finding using first derivative sign change."""
    peaks = []
    for i in range(1, len(data) - 1):
        if data[i] > data[i - 1] and data[i] > data[i + 1]:
            peaks.append(i)
    return peaks


def _generate_nudges(zones: list[EnergyZone], wake_time: datetime) -> list[NudgeEvent]:
    """Generate nudge events based on classified zones."""
    nudges = []
    for zone in zones:
        start_time = wake_time + timedelta(minutes=zone.start_minute)
        if zone.zone_type == "wake":
            nudges.append(NudgeEvent(
                minute=zone.start_minute,
                message="Get natural light exposure to clear sleep inertia",
                nudge_type="light_exposure",
            ))
        elif zone.zone_type == "afternoon_dip":
            nudges.append(NudgeEvent(
                minute=zone.start_minute,
                message="Consider a 20-minute nap to reduce sleep debt",
                nudge_type="nap",
            ))
        elif zone.zone_type == "melatonin_window":
            nudges.append(NudgeEvent(
                minute=zone.start_minute,
                message="Reduce blue light exposure — melatonin production starting",
                nudge_type="wind_down",
            ))
    return nudges
