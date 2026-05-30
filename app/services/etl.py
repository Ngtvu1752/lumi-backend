import uuid

from app.schemas.sleep import HealthConnectSyncRequest, SleepSessionCreate
from app.tasks.storage import insert_biometric_data, insert_sleep_sessions


async def ingest_health_connect_data(
    user_id: uuid.UUID,
    payload: HealthConnectSyncRequest,
) -> dict:
    """Dispatch Health Connect data to Celery storage workers.

    Sanitizes sleep sessions, serializes all records to dicts for JSON
    transport, and dispatches to the storage queue. Returns immediately
    without waiting for DB insert — the Celery worker handles persistence.
    """
    user_id_str = str(user_id)

    # Sanitize and serialize sleep sessions
    sessions = []
    for session in payload.sleep_sessions:
        sanitized = _sanitize_sleep_session(session)
        if sanitized is None:
            continue
        sessions.append({
            "start_time": sanitized.start_time.isoformat(),
            "end_time": sanitized.end_time.isoformat(),
            "duration_mins": sanitized.duration_mins,
            "session_type": sanitized.session_type,
        })

    # Serialize biometric records
    biometric_records = []
    if payload.heart_rate_records:
        for record in payload.heart_rate_records:
            biometric_records.append({
                "user_id": user_id_str,
                "time": record["time"],
                "metric_type": "heart_rate_bpm",
                "value": float(record["value"]),
            })

    if payload.steps_records:
        for record in payload.steps_records:
            biometric_records.append({
                "user_id": user_id_str,
                "time": record["time"],
                "metric_type": "steps",
                "value": float(record["value"]),
            })

    # Dispatch to Celery storage queue
    if sessions:
        insert_sleep_sessions.delay(user_id_str, sessions)

    if biometric_records:
        insert_biometric_data.delay(biometric_records)

    return {
        "sessions_dispatched": len(sessions),
        "biometrics_dispatched": len(biometric_records),
    }


def _sanitize_sleep_session(session: SleepSessionCreate):
    """Remove micro-awakenings (< 5 min) and classify session type."""
    if session.duration_mins < 5:
        return None  # Too short — likely noise

    # Auto-classify only if caller did not specify session_type
    if session.session_type is None:
        start_hour = session.start_time.hour
        session.session_type = "nap" if 10 <= start_hour < 18 else "nightly"

    return session
