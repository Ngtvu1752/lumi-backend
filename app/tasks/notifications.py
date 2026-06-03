"""Celery tasks for scheduling and sending habit nudge notifications.

Flow:
1. dispatch_all_users_nudges() — runs daily via Celery beat at midnight
   → fans out dispatch_daily_nudges() for each active user
2. dispatch_daily_nudges(user_id) — computes today's energy schedule,
   creates HabitLog entries, schedules send_scheduled_nudge() at each nudge time
3. send_scheduled_nudge(log_id) — fires at the scheduled time, sends FCM push
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone

from app.db.session import async_session_factory
from app.models.habit import Habit, HabitLog
from app.models.user import User
from app.tasks.worker import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="tasks.notifications.dispatch_daily_nudges", queue="analytics")
def dispatch_daily_nudges(user_id: str):
    """Compute today's nudge schedule and queue individual send tasks.

    Called once per user per day. Creates HabitLog entries for each nudge
    and schedules FCM sends at the exact circadian-optimized times.
    """
    asyncio.run(_dispatch_daily_nudges_async(user_id))


async def _dispatch_daily_nudges_async(user_id: str):
    uid = uuid.UUID(user_id)

    async with async_session_factory() as db:
        user = await db.get(User, uid)
        if not user:
            logger.warning(f"User {user_id} not found, skipping nudge dispatch")
            return

        # Get today's energy schedule (uses cache if available)
        from app.services.energy_schedule import get_user_energy_schedule

        schedule = await get_user_energy_schedule(db, uid)
        if not schedule or not schedule.nudges:
            logger.info(f"No nudges for user {user_id} today")
            return

        # Fetch habit names for notification titles
        from sqlalchemy import select

        habit_stmt = select(Habit)
        habit_result = await db.execute(habit_stmt)
        habit_map = {h.habit_id: h.name for h in habit_result.scalars().all()}

        # Create HabitLog for each nudge and schedule FCM send
        now = datetime.now(timezone.utc)
        scheduled_count = 0

        for nudge in schedule.nudges:
            nudge_time = nudge.time if hasattr(nudge, "time") else None
            if nudge_time is None:
                continue

            # Skip nudges that are already in the past
            if nudge_time <= now:
                logger.debug(f"Skipping past nudge {nudge.nudge_type} at {nudge_time}")
                continue

            # Create HabitLog entry
            log = HabitLog(
                user_id=uid,
                habit_id=nudge.nudge_type,
                scheduled_at=nudge_time,
                status="pending",
            )
            db.add(log)
            await db.flush()

            # Calculate delay from now to nudge time
            delay_seconds = (nudge_time - now).total_seconds()
            if delay_seconds <= 0:
                continue

            # Schedule FCM send task at the exact nudge time
            habit_name = habit_map.get(nudge.nudge_type, nudge.nudge_type)

            send_scheduled_nudge.apply_async(
                args=[
                    str(log.log_id),
                    str(uid),
                    nudge.nudge_type,
                    habit_name,
                    nudge.message,
                    nudge.priority,
                ],
                countdown=int(delay_seconds),
            )
            scheduled_count += 1

        await db.commit()

    logger.info(f"Scheduled {scheduled_count} nudges for user {user_id}")


@celery_app.task(
    name="tasks.notifications.send_scheduled_nudge",
    queue="analytics",
    acks_late=True,
)
def send_scheduled_nudge(
    log_id: str,
    user_id: str,
    habit_id: str,
    habit_name: str,
    message: str,
    priority: int,
):
    """Send a single nudge notification at its scheduled time.

    Triggered by countdown timer from dispatch_daily_nudges.
    Updates HabitLog status: pending → delivered (or skipped if too late).
    """
    asyncio.run(
        _send_scheduled_nudge_async(log_id, user_id, habit_id, habit_name, message, priority)
    )


async def _send_scheduled_nudge_async(
    log_id: str,
    user_id: str,
    habit_id: str,
    habit_name: str,
    message: str,
    priority: int,
):
    from app.services.notification import send_nudge_notification

    async with async_session_factory() as db:
        log = await db.get(HabitLog, uuid.UUID(log_id))
        if not log:
            logger.warning(f"HabitLog {log_id} not found")
            return

        # If already delivered/completed, skip
        if log.status != "pending":
            logger.info(f"HabitLog {log_id} already {log.status}, skipping")
            return

        # Check if we're too late (>15 min past scheduled time)
        now = datetime.now(timezone.utc)
        if now > log.scheduled_at + timedelta(minutes=15):
            log.status = "skipped"
            await db.commit()
            logger.info(f"HabitLog {log_id} skipped — too late (scheduled={log.scheduled_at})")
            return

        # Send FCM notification
        uid = uuid.UUID(user_id)
        sent = await send_nudge_notification(
            user_id=uid,
            habit_id=habit_id,
            habit_name=habit_name,
            message=message,
            priority=priority,
        )

        # Update log status
        if sent > 0:
            log.status = "delivered"
            logger.info(f"HabitLog {log_id} delivered to {sent} device(s)")
        else:
            log.status = "delivered"  # Mark delivered even if no device (algorithm ran)
            logger.info(f"HabitLog {log_id} marked delivered (no active devices)")

        await db.commit()


@celery_app.task(name="tasks.notifications.dispatch_all_users_nudges", queue="analytics")
def dispatch_all_users_nudges():
    """Daily task: dispatch nudge schedules for all active users.

    Should be triggered by Celery beat at midnight UTC.
    Fans out individual dispatch_daily_nudges tasks.
    """
    asyncio.run(_dispatch_all_users_async())


async def _dispatch_all_users_async():
    from sqlalchemy import select

    async with async_session_factory() as db:
        # Get all users who have had activity in the last 30 days
        # (avoids scheduling for abandoned accounts)
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        stmt = select(User.user_id).where(User.created_at >= cutoff)
        result = await db.execute(stmt)
        user_ids = [str(row[0]) for row in result.all()]

    if not user_ids:
        logger.info("No active users found for nudge dispatch")
        return

    # Fan out individual tasks
    for uid in user_ids:
        dispatch_daily_nudges.delay(uid)

    logger.info(f"Dispatched nudge scheduling for {len(user_ids)} users")
