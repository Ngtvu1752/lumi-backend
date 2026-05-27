import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.schemas.energy import EnergyScheduleResponse
from app.services.energy_schedule import get_user_energy_schedule

router = APIRouter(prefix="/energy", tags=["energy"])


@router.get("/schedule", response_model=EnergyScheduleResponse)
async def get_energy_schedule(
    date: datetime | None = Query(None, description="Date to compute schedule for (defaults to today)"),
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get 24-hour energy schedule with zones and nudges.

    Returns cached result if available (TTL 24h), otherwise
    triggers full computation pipeline.
    """
    return await get_user_energy_schedule(db, user_id, date)
