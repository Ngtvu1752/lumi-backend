import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.models.habit import Habit, HabitLog, UserHabitPreference
from app.schemas.habit import HabitLogCreate, HabitLogResponse, HabitPreferenceUpdate, HabitResponse
from app.services.habit_seed import seed_habits

router = APIRouter(prefix="/habits", tags=["habits"])


@router.get("", response_model=list[HabitResponse])
async def list_habits(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """List all active habits with the user's enabled/disabled status."""
    # Get all active habits
    stmt = select(Habit).where(Habit.is_active == True).order_by(Habit.default_priority.desc())
    result = await db.execute(stmt)
    habits = result.scalars().all()

    # Get user's preferences
    pref_stmt = select(UserHabitPreference).where(UserHabitPreference.user_id == user_id)
    pref_result = await db.execute(pref_stmt)
    preferences = {p.habit_id: p.enabled for p in pref_result.scalars().all()}

    # Merge: default enabled=True if no preference set
    return [
        HabitResponse(
            habit_id=h.habit_id,
            name=h.name,
            description=h.description,
            zone_type=h.zone_type,
            default_priority=h.default_priority,
            enabled=preferences.get(h.habit_id, True),
        )
        for h in habits
    ]


@router.put("/{habit_id}/preference", response_model=HabitResponse)
async def update_habit_preference(
    habit_id: str,
    payload: HabitPreferenceUpdate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Enable or disable a habit for the current user."""
    # Verify habit exists
    habit = await db.get(Habit, habit_id)
    if not habit:
        from app.core.exceptions import NotFoundError
        raise NotFoundError(f"Habit '{habit_id}' not found")

    # Upsert preference
    pref = await db.get(UserHabitPreference, (user_id, habit_id))
    if pref:
        pref.enabled = payload.enabled
    else:
        pref = UserHabitPreference(user_id=user_id, habit_id=habit_id, enabled=payload.enabled)
        db.add(pref)

    await db.flush()

    # Invalidate energy cache so next schedule reflects the change
    from app.cache.energy_cache import invalidate_energy_cache
    today = datetime.now(timezone.utc)
    await invalidate_energy_cache(user_id, today)

    return HabitResponse(
        habit_id=habit.habit_id,
        name=habit.name,
        description=habit.description,
        zone_type=habit.zone_type,
        default_priority=habit.default_priority,
        enabled=pref.enabled,
    )


@router.post("/log", response_model=HabitLogResponse)
async def create_habit_log(
    payload: HabitLogCreate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Log a nudge delivery, acknowledgment, or completion."""
    log = HabitLog(
        user_id=user_id,
        habit_id=payload.habit_id,
        scheduled_at=payload.scheduled_at,
        status=payload.status,
    )
    db.add(log)
    await db.flush()
    return log


@router.get("/log", response_model=list[HabitLogResponse])
async def get_habit_logs(
    habit_id: str | None = None,
    days: int = 30,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get habit log history for the current user."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    stmt = (
        select(HabitLog)
        .where(HabitLog.user_id == user_id)
        .where(HabitLog.created_at >= cutoff)
        .order_by(HabitLog.created_at.desc())
    )
    if habit_id:
        stmt = stmt.where(HabitLog.habit_id == habit_id)

    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/seed", response_model=dict)
async def seed_habits_endpoint(
    db: AsyncSession = Depends(get_db),
):
    """Seed all 16 science-based habits into the database (admin utility)."""
    count = await seed_habits(db)
    return {"seeded": count}
