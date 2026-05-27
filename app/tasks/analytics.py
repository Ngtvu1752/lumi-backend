import asyncio
import uuid
from datetime import datetime, timezone

from app.db.session import async_session_factory
from app.services.calibration import calibrate_snop
from app.services.energy_schedule import get_user_energy_schedule
from app.tasks.worker import celery_app


@celery_app.task(name="tasks.analytics.recalculate_energy", queue="analytics")
def recalculate_energy(user_id: str):
    """Trigger full energy schedule recalculation for a user.

    Called after new sleep data is ingested. Runs on dedicated
    analytics worker to avoid competing with storage inserts.
    """
    asyncio.run(_recalculate_async(user_id))


async def _recalculate_async(user_id: str):
    uid = uuid.UUID(user_id)
    async with async_session_factory() as db:
        # Recalibrate SNOP with latest data
        await calibrate_snop(db, uid)

        # Recompute energy schedule (will invalidate cache internally)
        await get_user_energy_schedule(db, uid)


@celery_app.task(name="tasks.analytics.batch_recalculate", queue="analytics")
def batch_recalculate(user_ids: list[str]):
    """Batch recalculation for morning sync burst.

    Triggered when many users wake up and sync simultaneously.
    """
    for uid in user_ids:
        recalculate_energy.delay(uid)


@celery_app.task(name="tasks.analytics.calibrate_snop", queue="analytics")
def calibrate_snop_task(user_id: str):
    """Standalone SNOP calibration task."""
    asyncio.run(_calibrate_async(user_id))


async def _calibrate_async(user_id: str):
    uid = uuid.UUID(user_id)
    async with async_session_factory() as db:
        await calibrate_snop(db, uid)
        await db.commit()
