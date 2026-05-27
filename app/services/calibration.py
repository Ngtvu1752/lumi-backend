import uuid

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sleep_session import SleepSession
from app.models.survey import UserSurveyResponse
from app.models.user import User


# Actigraphy reference table: (age_group, gender) -> SNOP hours
ACTIGRAPHY_REFERENCE = {
    ("18-25", "M"): 7.5, ("18-25", "F"): 7.75,
    ("26-35", "M"): 7.25, ("26-35", "F"): 7.5,
    ("36-45", "M"): 7.0, ("36-45", "F"): 7.25,
    ("46-60", "M"): 7.0, ("46-60", "F"): 7.0,
}


async def calibrate_snop(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> float:
    """Calibrate SNOP using seed data + available Health Connect data.

    Phase 1 (seed): use onboarding survey to estimate SNOP
    Phase 2 (dynamic): replace with EMA of actual sleep data as it accumulates
    """
    user = await db.get(User, user_id)
    if not user:
        raise ValueError(f"User {user_id} not found")

    # Get actual sleep data
    stmt = (
        select(SleepSession)
        .where(SleepSession.user_id == user_id)
        .where(SleepSession.session_type == "nightly")
        .order_by(SleepSession.start_time.desc())
        .limit(14)
    )
    result = await db.execute(stmt)
    sessions = result.scalars().all()

    if len(sessions) >= 7:
        # Dynamic calibration: EMA of actual sleep durations
        durations = np.array([s.duration_mins / 60.0 for s in sessions])
        snop = _ema_smoothing(durations)
    else:
        # Seed calibration from survey
        snop = await _seed_from_survey(db, user_id)

    user.snop_hours = snop
    await db.flush()
    return snop


async def _seed_from_survey(db: AsyncSession, user_id: uuid.UUID) -> float:
    """Estimate SNOP from onboarding survey responses."""
    stmt = select(UserSurveyResponse).where(UserSurveyResponse.user_id == user_id)
    result = await db.execute(stmt)
    responses = {r.question_id: r.answer_key for r in result.scalars().all()}

    age = int(responses.get("age", "30"))
    gender = responses.get("gender", "M")
    sleep_schedule = responses.get("sleep_schedule", "7-8h")

    # Map age to group
    if age <= 25:
        age_group = "18-25"
    elif age <= 35:
        age_group = "26-35"
    elif age <= 45:
        age_group = "36-45"
    else:
        age_group = "46-60"

    base_snop = ACTIGRAPHY_REFERENCE.get((age_group, gender), 7.5)

    # Adjust based on self-reported sleep need
    if "6" in sleep_schedule:
        base_snop = min(base_snop, 6.5)
    elif "9" in sleep_schedule:
        base_snop = max(base_snop, 8.5)

    return base_snop


def _ema_smoothing(durations: np.ndarray, alpha: float = 0.3) -> float:
    """Exponential moving average of sleep durations."""
    ema = durations[0]
    for d in durations[1:]:
        ema = alpha * d + (1 - alpha) * ema
    return float(ema)
