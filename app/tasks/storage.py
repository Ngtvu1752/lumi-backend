import asyncio
from datetime import datetime

from app.db.session import async_session_factory
from app.models.biometric import BiometricData
from app.models.sleep_session import SleepSession
from app.tasks.worker import celery_app


@celery_app.task(name="tasks.storage.insert_sleep_sessions", queue="storage")
def insert_sleep_sessions(user_id: str, sessions: list[dict]):
    """Batch INSERT sleep sessions into TimescaleDB hypertable.

    Runs as a dedicated storage worker to avoid blocking the API.
    After successful insert, chains recalculate_energy on the analytics queue.
    """
    asyncio.run(_insert_sessions_async(user_id, sessions))


async def _insert_sessions_async(user_id: str, sessions: list[dict]):
    from app.tasks.analytics import recalculate_energy

    async with async_session_factory() as db:
        for s in sessions:
            db.add(SleepSession(
                user_id=user_id,
                start_time=datetime.fromisoformat(s["start_time"]),
                end_time=datetime.fromisoformat(s["end_time"]),
                duration_mins=s["duration_mins"],
                session_type=s["session_type"],
            ))
        await db.commit()

    # Chain analytics: recalculate energy after storage completes
    recalculate_energy.delay(user_id)


@celery_app.task(name="tasks.storage.insert_biometric_data", queue="storage")
def insert_biometric_data(records: list[dict]):
    """Batch INSERT biometric data into TimescaleDB hypertable.

    Uses chunked inserts for large payloads from wearable syncs.
    """
    asyncio.run(_insert_biometrics_async(records))


async def _insert_biometrics_async(records: list[dict]):
    CHUNK_SIZE = 1000
    async with async_session_factory() as db:
        for i in range(0, len(records), CHUNK_SIZE):
            chunk = records[i : i + CHUNK_SIZE]
            for r in chunk:
                db.add(BiometricData(
                    user_id=r["user_id"],
                    time=datetime.fromisoformat(r["time"]),
                    metric_type=r["metric_type"],
                    value=r["value"],
                ))
            await db.flush()
        await db.commit()
