import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id
from app.cache.energy_cache import invalidate_energy_cache
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import SnopUpdateRequest, UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.patch("/me/snop", response_model=UserResponse)
async def update_snop(
    payload: SnopUpdateRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Manual SNOP override — allows user to adjust their sleep need constant.

    Updates snop_hours and invalidates today's cached energy schedule
    so the next request recalculates with the new value.
    """
    user = await db.get(User, user_id)
    if not user:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("User not found")

    user.snop_hours = payload.snop_hours
    await db.flush()

    # Invalidate today's energy cache so next GET /energy/schedule recalculates
    today = datetime.now(timezone.utc)
    await invalidate_energy_cache(user_id, today)

    return user
