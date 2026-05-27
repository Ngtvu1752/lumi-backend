import numpy as np

from app.core.config import settings

AMPLITUDES = np.array(settings.HARMONIC_AMPLITUDES)  # [0.97, 0.22, 0.07, 0.03, 0.001]
TAU = settings.CIRCADIAN_PERIOD  # 24.2 hours


def compute_process_c(
    t_hours: np.ndarray,
    phi: float = 0.0,
) -> np.ndarray:
    """Compute circadian alertness signal C(k) using 5-harmonic sinusoidal model.

    C(k) = sum_{i=1}^{5} a_i * sin(i * 2*pi/tau * t + phi)

    Args:
        t_hours: array of time points in hours
        phi: initial circadian phase (radians), personalized per user

    Returns:
        C(k) array of circadian signal values
    """
    result = np.zeros_like(t_hours, dtype=np.float64)

    for i, amplitude in enumerate(AMPLITUDES, start=1):
        result += amplitude * np.sin(i * 2.0 * np.pi / TAU * t_hours + phi)

    return result


def estimate_phase_from_sleep_times(
    bedtimes: list[float],
    wake_times: list[float],
) -> float:
    """Estimate initial circadian phase phi from historical sleep/wake times.

    Uses the midpoint of sleep as a proxy for the nadir of the circadian cycle.
    The nadir of Process C typically occurs ~2h before habitual wake time.

    Args:
        bedtimes: list of bedtime hours (e.g. 23.0 for 11 PM)
        wake_times: list of wake time hours (e.g. 7.0 for 7 AM)

    Returns:
        Estimated phi in radians
    """
    if not bedtimes or not wake_times:
        return 0.0

    # Average midpoint of sleep
    midpoints = []
    for bed, wake in zip(bedtimes, wake_times):
        if wake < bed:
            wake += 24.0
        midpoints.append((bed + wake) / 2.0)

    avg_midpoint = np.mean(midpoints) % 24.0

    # Nadir of C(k) occurs at ~2h before wake time
    # The nadir of sin(x) is at -pi/2, so we solve for phi
    nadir_hour = avg_midpoint - 2.0
    phi = -np.pi / 2.0 - 2.0 * np.pi / TAU * nadir_hour

    return phi
