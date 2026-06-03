import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.models.device import DeviceToken
from app.schemas.device import DeviceTokenRegister, DeviceTokenResponse

router = APIRouter(prefix="/devices", tags=["devices"])


@router.post("/register", response_model=DeviceTokenResponse)
async def register_device(
    payload: DeviceTokenRegister,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Register or update an FCM device token for push notifications.

    If the token already exists for this user, update it.
    If the token belongs to another user, reassign it.
    """
    stmt = select(DeviceToken).where(DeviceToken.token == payload.token)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        # Token exists — update ownership and reactivate
        existing.user_id = user_id
        existing.platform = payload.platform
        existing.is_active = True
        existing.updated_at = datetime.now(timezone.utc)
        await db.flush()
        return existing

    # New token
    device = DeviceToken(
        user_id=user_id,
        token=payload.token,
        platform=payload.platform,
    )
    db.add(device)
    await db.flush()
    return device


@router.delete("/{token}")
async def deactivate_device(
    token: str,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Deactivate a device token (e.g., on logout)."""
    stmt = select(DeviceToken).where(
        DeviceToken.token == token,
        DeviceToken.user_id == user_id,
    )
    result = await db.execute(stmt)
    device = result.scalar_one_or_none()

    if not device:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("Device token not found")

    device.is_active = False
    device.updated_at = datetime.now(timezone.utc)
    await db.flush()

    return {"status": "deactivated", "token": token}


@router.get("", response_model=list[DeviceTokenResponse])
async def list_devices(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """List all active device tokens for the current user."""
    stmt = (
        select(DeviceToken)
        .where(DeviceToken.user_id == user_id, DeviceToken.is_active == True)
        .order_by(DeviceToken.created_at.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()
