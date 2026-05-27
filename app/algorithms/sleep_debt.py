import numpy as np

from app.core.config import settings

WINDOW_DAYS = settings.SLEEP_DEBT_WINDOW  # 14 days
WARNING_THRESHOLD = settings.SLEEP_DEBT_WARNING_THRESHOLD  # 300 minutes (5 hours)


def compute_sleep_debt(
    snop_mins: float,
    actual_sleep_mins: np.ndarray,
) -> float:
    """Compute cumulative sleep debt over the 14-day sliding window.

    Sleep Debt = sum(SNOP - actual_sleep_i) for i in 1..14

    Args:
        snop_mins: Sleep Need for Optimal Performance in minutes
        actual_sleep_mins: array of daily total sleep (nightly + naps) in minutes,
                           length should be <= WINDOW_DAYS

    Returns:
        Cumulative sleep debt in minutes (positive = in debt)
    """
    if len(actual_sleep_mins) == 0:
        return 0.0

    # Use available data up to WINDOW_DAYS
    recent = actual_sleep_mins[-WINDOW_DAYS:]
    debt = np.sum(snop_mins - recent)
    return float(max(debt, 0.0))


def is_above_warning_threshold(sleep_debt_mins: float) -> bool:
    return sleep_debt_mins > WARNING_THRESHOLD


def format_sleep_debt(debt_mins: float) -> str:
    """Format sleep debt as human-readable string, e.g. '4h 30m'."""
    hours = int(debt_mins // 60)
    minutes = int(debt_mins % 60)
    return f"{hours}h {minutes}m"
