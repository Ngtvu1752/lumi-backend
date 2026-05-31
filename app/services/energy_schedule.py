import uuid
from datetime import datetime, timedelta, timezone

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.algorithms.process_c import estimate_phase_from_sleep_times
from app.algorithms.process_s import compute_process_s
from app.algorithms.sleep_debt import compute_sleep_debt, format_sleep_debt
from app.algorithms.synthesis import compute_energy_schedule
from app.cache.energy_cache import get_cached_energy, set_cached_energy
from app.models.sleep_session import SleepSession
from app.models.user import User
from app.schemas.energy import EnergyScheduleResponse
from app.services.exertion import compute_exertion_score, exertion_snop_adjustment


async def get_user_energy_schedule(
    db: AsyncSession,
    user_id: uuid.UUID,
    date: datetime | None = None,
) -> EnergyScheduleResponse:
    """Orchestrate full energy schedule computation for a user.

    Pipeline:
    1. Check Redis cache
    2. Fetch sleep history
    3. Compute sleep debt
    4. Estimate circadian phase
    5. Compute exertion-adjusted SNOP
    6. Compute Process S at wake
    7. Run synthesis to get 24h energy curve
    8. Cache result
    """
    if date is None:
        date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    # 1. Check cache
    cached = await get_cached_energy(user_id, date)
    if cached:
        return cached

    user = await db.get(User, user_id)
    if not user:
        raise ValueError(f"User {user_id} not found")

    # 2. Fetch last 14 days of sleep
    cutoff = date - timedelta(days=14)
    stmt = (
        select(SleepSession)
        .where(SleepSession.user_id == user_id)
        .where(SleepSession.start_time >= cutoff)
        .order_by(SleepSession.start_time)
    )
    result = await db.execute(stmt)
    sessions = result.scalars().all()

    # 3. Compute sleep debt
    daily_mins = _aggregate_daily_sleep(sessions, date)
    debt_mins = compute_sleep_debt(user.snop_hours * 60, daily_mins)

    # 4. Estimate phase from recent bedtimes/wake times
    bedtimes = [s.start_time.hour + s.start_time.minute / 60.0 for s in sessions[-7:]]
    wake_times = [s.end_time.hour + s.end_time.minute / 60.0 for s in sessions[-7:]]
    phi = estimate_phase_from_sleep_times(bedtimes, wake_times)

    # 5. Exertion-adjusted SNOP (high activity → more recovery sleep needed)
    exertion = await compute_exertion_score(db, user_id)
    snop_multiplier = exertion_snop_adjustment(exertion)
    effective_snop_mins = user.snop_hours * 60 * snop_multiplier

    # 6. Compute Process S at wake (higher debt = higher starting H)
    h_at_wake = min(debt_mins / effective_snop_mins, 1.0) if effective_snop_mins > 0 else 0.0

    # 7. Get today's wake time
    today_sessions = [s for s in sessions if s.start_time.date() == date.date()]
    if today_sessions:
        wake_time = max(s.end_time for s in today_sessions)
    else:
        wake_time = date.replace(hour=7, minute=0)  # default 7 AM

    # 8. Run synthesis
    schedule = compute_energy_schedule(wake_time, h_at_wake, phi)

    # 9. Build response
    from app.schemas.energy import EnergyPoint, EnergyZone, NudgeEvent

    points = []
    for i, val in enumerate(schedule.energy_values):
        t = wake_time + timedelta(minutes=i * 5)
        points.append(EnergyPoint(time=t, value=float(val)))

    zones = [
        EnergyZone(
            zone_type=z.zone_type,
            start_time=wake_time + timedelta(minutes=z.start_minute),
            end_time=wake_time + timedelta(minutes=z.end_minute),
        )
        for z in schedule.zones
    ]

    nudges = [
        NudgeEvent(
            time=wake_time + timedelta(minutes=n.minute),
            message=n.message,
            nudge_type=n.nudge_type,
        )
        for n in schedule.nudges
    ]

    response = EnergyScheduleResponse(
        user_id=user_id,
        date=date,
        energy_points=points,
        zones=zones,
        nudges=nudges,
        energy_potential=schedule.energy_potential_score,
        is_cached=False,
    )

    # 10. Cache
    await set_cached_energy(user_id, date, response)

    return response


def _aggregate_daily_sleep(
    sessions: list[SleepSession],
    target_date: datetime,
) -> np.ndarray:
    """Aggregate total sleep minutes per day for the 14-day window."""
    daily: dict[str, float] = {}
    for s in sessions:
        day_key = s.start_time.strftime("%Y-%m-%d")
        daily[day_key] = daily.get(day_key, 0.0) + s.duration_mins

    # Build array for last 14 days
    result = []
    for i in range(14):
        day = target_date - timedelta(days=13 - i)
        key = day.strftime("%Y-%m-%d")
        result.append(daily.get(key, 0.0))

    return np.array(result)
