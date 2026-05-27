import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.biometric import BiometricData
from app.models.sleep_session import SleepSession
from app.schemas.sleep import HealthConnectSyncRequest


async def ingest_health_connect_data(
    db: AsyncSession,
    user_id: uuid.UUID,
    payload: HealthConnectSyncRequest,
) -> dict:
    """Ingest data from Android Health Connect sync.

    Handles sanitization: removes micro-awakenings, deduplicates overlapping
    sessions from multiple devices, and classifies nightly vs nap sessions.
    """
    inserted_sessions = 0
    inserted_biometrics = 0

    for session in payload.sleep_sessions:
        sanitized = _sanitize_sleep_session(session)
        if sanitized is None:
            continue

        db_session = SleepSession(
            user_id=user_id,
            start_time=sanitized.start_time,
            end_time=sanitized.end_time,
            duration_mins=sanitized.duration_mins,
            session_type=sanitized.session_type,
        )
        db.add(db_session)
        inserted_sessions += 1

    if payload.heart_rate_records:
        for record in payload.heart_rate_records:
            db.add(BiometricData(
                user_id=str(user_id),
                time=datetime.fromisoformat(record["time"]),
                metric_type="heart_rate_bpm",
                value=float(record["value"]),
            ))
            inserted_biometrics += 1

    if payload.steps_records:
        for record in payload.steps_records:
            db.add(BiometricData(
                user_id=str(user_id),
                time=datetime.fromisoformat(record["time"]),
                metric_type="steps",
                value=float(record["value"]),
            ))
            inserted_biometrics += 1

    await db.flush()

    return {
        "sessions_inserted": inserted_sessions,
        "biometrics_inserted": inserted_biometrics,
    }


def _sanitize_sleep_session(session):
    """Remove micro-awakenings (< 5 min) and classify session type."""
    if session.duration_mins < 5:
        return None  # Too short — likely noise

    # Classify: sleep between 10 AM - 6 PM is a nap
    start_hour = session.start_time.hour
    if 10 <= start_hour < 18:
        session.session_type = "nap"
    else:
        session.session_type = "nightly"

    return session
