import uuid
from datetime import datetime, timedelta, timezone

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.biometric import BiometricData

# Physiological defaults (can be personalized later from user profile)
RESTING_HR = 60.0   # bpm — typical resting heart rate
MAX_HR = 200.0      # bpm — typical max heart rate (age-dependent)
TARGET_SNOP_BOOST = 0.05  # max +5% SNOP for highest exertion days


async def compute_exertion_score(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> float:
    """Compute daily exertion score from heart rate data.

    Queries heart rate records from the past 24 hours and calculates
    a normalized exertion score based on how much the average HR exceeds
    the resting baseline.

    Returns:
        Exertion score in [0.0, 1.0] where 0 = no exertion, 1 = max exertion.
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=24)

    stmt = (
        select(BiometricData.value)
        .where(BiometricData.user_id == str(user_id))
        .where(BiometricData.metric_type == "heart_rate_bpm")
        .where(BiometricData.time >= cutoff)
    )
    result = await db.execute(stmt)
    hr_values = [row[0] for row in result.fetchall()]

    if not hr_values:
        return 0.0  # No data — assume no exertion

    avg_hr = float(np.mean(hr_values))

    # Normalize: resting=0, max=1
    score = (avg_hr - RESTING_HR) / (MAX_HR - RESTING_HR)
    return float(np.clip(score, 0.0, 1.0))


def exertion_snop_adjustment(exertion_score: float) -> float:
    """Convert exertion score to a SNOP multiplier.

    High exertion days require more sleep for recovery. The adjustment
    is conservative: +0% at rest, up to +5% at max exertion.

    Args:
        exertion_score: normalized [0, 1] exertion level

    Returns:
        Multiplier to apply to SNOP (e.g., 1.03 = +3% sleep need)
    """
    return 1.0 + TARGET_SNOP_BOOST * exertion_score
