"""Push notification service using Firebase Cloud Messaging (FCM).

Sends nudge notifications to user devices at circadian-optimized times.
Gracefully degrades if FCM credentials are not configured (logs warning).
"""

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import async_session_factory
from app.models.device import DeviceToken

logger = logging.getLogger(__name__)

# Lazy-init Firebase app (initialized once on first use)
_firebase_initialized = False
_firebase_app = None


def _get_firebase_app():
    """Initialize Firebase Admin SDK lazily. Returns None if not configured."""
    global _firebase_initialized, _firebase_app

    if _firebase_initialized:
        return _firebase_app

    _firebase_initialized = True

    cred_path = settings.FCM_CREDENTIALS_PATH
    if not cred_path:
        logger.warning(
            "FCM_CREDENTIALS_PATH not configured. "
            "Push notifications will be logged but not sent."
        )
        return None

    try:
        import firebase_admin
        from firebase_admin import credentials

        cred = credentials.Certificate(cred_path)
        _firebase_app = firebase_admin.initialize_app(cred)
        logger.info("Firebase Admin SDK initialized successfully")
        return _firebase_app
    except Exception as e:
        logger.error(f"Failed to initialize Firebase Admin SDK: {e}")
        return None


def _send_fcm_message(token: str, title: str, body: str, data: dict) -> bool:
    """Send a single FCM message. Returns True if sent successfully."""
    app = _get_firebase_app()
    if app is None:
        # FCM not configured — log for debugging
        logger.info(f"[FCM MOCK] title='{title}', body='{body}', data={data}")
        return False

    try:
        from firebase_admin import messaging

        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data={k: str(v) for k, v in data.items()},
            token=token,
            android=messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(
                    channel_id="habit_nudges",
                    sound="default",
                ),
            ),
        )
        response = messaging.send(message)
        logger.info(f"FCM message sent: {response}")
        return True
    except Exception as e:
        logger.error(f"FCM send failed for token={token[:20]}...: {e}")
        return False


async def send_nudge_notification(
    user_id: uuid.UUID,
    habit_id: str,
    habit_name: str,
    message: str,
    priority: int,
) -> int:
    """Send a nudge push notification to all active devices of a user.

    Args:
        user_id: target user
        habit_id: the habit being nudged
        habit_name: display name of the habit
        message: nudge message text
        priority: 1-5 priority level

    Returns:
        Number of notifications successfully sent.
    """
    async with async_session_factory() as db:
        # Fetch active device tokens
        stmt = select(DeviceToken).where(
            DeviceToken.user_id == user_id,
            DeviceToken.is_active == True,
        )
        result = await db.execute(stmt)
        devices = result.scalars().all()

        if not devices:
            logger.info(f"No active devices for user {user_id}, skipping notification")
            return 0

        sent_count = 0
        invalid_tokens = []

        for device in devices:
            success = _send_fcm_message(
                token=device.token,
                title=habit_name,
                body=message,
                data={
                    "habit_id": habit_id,
                    "priority": str(priority),
                    "user_id": str(user_id),
                },
            )
            if success:
                sent_count += 1
            else:
                # If Firebase says token is invalid, deactivate it
                # (In production, catch firebase_admin.exceptions.FirebaseError)
                pass

        # Deactivate any invalid tokens
        if invalid_tokens:
            await db.execute(
                update(DeviceToken)
                .where(DeviceToken.token.in_(invalid_tokens))
                .values(is_active=False, updated_at=datetime.now(timezone.utc))
            )
            await db.flush()

        return sent_count


async def send_nudge_notification_sync(
    user_id: str,
    habit_id: str,
    habit_name: str,
    message: str,
    priority: int,
) -> int:
    """Synchronous-friendly wrapper for use in Celery tasks."""
    uid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
    return await send_nudge_notification(uid, habit_id, habit_name, message, priority)
