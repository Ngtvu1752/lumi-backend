import numpy as np
from scipy.integrate import solve_ivp

from app.core.config import settings

TAU_R = settings.TAU_R  # 18.2 hours — rise constant (awake)
TAU_D = settings.TAU_D  # 4.2 hours — decay constant (asleep)


def _ode_wake(t: float, y: list[float]) -> list[float]:
    """dH/dt = (1 - H) / tau_r — exponential rise toward 1 during wake."""
    return [(1.0 - y[0]) / TAU_R]


def _ode_sleep(t: float, y: list[float]) -> list[float]:
    """dH/dt = -H / tau_d — exponential decay toward 0 during sleep."""
    return [-y[0] / TAU_D]


def compute_process_s(
    t_hours: np.ndarray,
    sleep_mask: np.ndarray,
    h_initial: float = 0.0,
) -> np.ndarray:
    """Compute homeostatic sleep pressure H(t) using SciPy ODE solver.

    Solves the Borbély Process S differential equation segment-by-segment
    at sleep/wake boundaries using scipy.integrate.solve_ivp with RK45.

    During wake:  dH/dt = (1 - H) / tau_r
    During sleep: dH/dt = -H / tau_d

    Args:
        t_hours: array of time points in hours
        sleep_mask: boolean array, True when user is asleep at each time point
        h_initial: initial H value at t[0] (0.0 = fully rested)

    Returns:
        H(t) array of sleep pressure values in [0, 1]
    """
    n = len(t_hours)
    if n == 0:
        return np.array([], dtype=np.float64)

    h = np.empty(n, dtype=np.float64)
    h[0] = h_initial

    if n == 1:
        return h

    # Find boundaries where sleep/wake state changes
    changes = np.where(np.diff(sleep_mask.astype(int)))[0] + 1
    # Split indices into contiguous segments of the same state
    segment_starts = np.concatenate([[0], changes])
    segment_ends = np.concatenate([changes, [n]])

    h_current = h_initial

    for seg_start, seg_end in zip(segment_starts, segment_ends):
        is_asleep = sleep_mask[seg_start]
        ode_fn = _ode_sleep if is_asleep else _ode_wake

        seg_t = t_hours[seg_start:seg_end]

        if len(seg_t) < 2:
            h[seg_start] = h_current
            continue

        # Solve ODE over this contiguous segment using RK45
        sol = solve_ivp(
            fun=ode_fn,
            t_span=(seg_t[0], seg_t[-1]),
            y0=[h_current],
            t_eval=seg_t,
            method="RK45",
            rtol=1e-8,
            atol=1e-10,
        )

        if not sol.success:
            # Fallback: analytical solution per point (should not happen)
            h_seg = np.empty(len(seg_t), dtype=np.float64)
            h_seg[0] = h_current
            dt = np.diff(seg_t)
            for j in range(len(dt)):
                if is_asleep:
                    h_seg[j + 1] = h_seg[j] * np.exp(-dt[j] / TAU_D)
                else:
                    h_seg[j + 1] = 1.0 - (1.0 - h_seg[j]) * np.exp(-dt[j] / TAU_R)
            h[seg_start:seg_end] = h_seg
            h_current = h_seg[-1]
        else:
            h[seg_start:seg_end] = sol.y[0]
            h_current = float(sol.y[0, -1])

    # Clip to valid range [0, 1] to handle floating-point drift
    np.clip(h, 0.0, 1.0, out=h)

    return h
