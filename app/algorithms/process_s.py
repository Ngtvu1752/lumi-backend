import numpy as np

from app.core.config import settings

TAU_R = settings.TAU_R  # 18.2 hours — rise constant (awake)
TAU_D = settings.TAU_D  # 4.2 hours — decay constant (asleep)


def compute_process_s(
    t_hours: np.ndarray,
    sleep_mask: np.ndarray,
    h_initial: float = 0.0,
) -> np.ndarray:
    """Compute homeostatic sleep pressure H(t) using Borbély Process S model.

    During wake:  dH/dt = (1 - H) / tau_r
    During sleep: dH/dt = -H / tau_d

    Args:
        t_hours: array of time points in hours (e.g. 0.0, 0.083, ... for 5-min intervals)
        sleep_mask: boolean array, True when user is asleep at each time point
        h_initial: initial H value at t[0] (0.0 = fully rested)

    Returns:
        H(t) array of sleep pressure values in [0, 1]
    """
    h = np.empty_like(t_hours, dtype=np.float64)
    h[0] = h_initial

    for i in range(1, len(t_hours)):
        dt = t_hours[i] - t_hours[i - 1]
        if sleep_mask[i]:
            # Sleep: exponential decay toward 0
            h[i] = h[i - 1] * np.exp(-dt / TAU_D)
        else:
            # Awake: exponential rise toward 1
            h[i] = 1.0 - (1.0 - h[i - 1]) * np.exp(-dt / TAU_R)

    return h


def compute_process_s_vectorized(
    t_hours: np.ndarray,
    sleep_mask: np.ndarray,
    h_initial: float = 0.0,
) -> np.ndarray:
    """Vectorized version for batch computation across multiple days.

    Uses segment-based computation to avoid per-sample loop.
    """
    h = np.empty_like(t_hours, dtype=np.float64)
    h[0] = h_initial

    # Find segments of contiguous sleep/wake
    changes = np.where(np.diff(sleep_mask.astype(int)))[0] + 1
    segments = np.split(np.arange(len(t_hours)), changes)

    for seg_idx, indices in enumerate(segments):
        start = indices[0]
        is_asleep = sleep_mask[start]

        if start == 0:
            seg_h = np.empty(len(indices), dtype=np.float64)
            seg_h[0] = h_initial
        else:
            seg_h = np.empty(len(indices), dtype=np.float64)
            seg_h[0] = h[start - 1] if start > 0 else h_initial

        dt = np.diff(t_hours[indices])

        if is_asleep:
            for j in range(1, len(indices)):
                seg_h[j] = seg_h[j - 1] * np.exp(-dt[j - 1] / TAU_D)
        else:
            for j in range(1, len(indices)):
                seg_h[j] = 1.0 - (1.0 - seg_h[j - 1]) * np.exp(-dt[j - 1] / TAU_R)

        h[indices] = seg_h

    return h
