import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.models.sleep_session import SleepSession
from app.models.user import User
from app.schemas.sleep import HealthConnectSyncRequest, SleepDebtResponse, SleepSessionCreate, SleepSessionResponse
from app.services.etl import ingest_health_connect_data
from app.tasks.storage import insert_sleep_sessions
from app.algorithms.sleep_debt import compute_sleep_debt, format_sleep_debt

router = APIRouter(prefix="/sleep", tags=["sleep"])


@router.post("/sync", response_model=dict)
async def sync_health_connect(
    payload: HealthConnectSyncRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Ingest sleep data from Android Health Connect.

    Dispatches data to Celery storage workers for async DB insert.
    Returns immediately — does not block on persistence.
    Energy recalculation is chained automatically after storage completes.
    """
    result = await ingest_health_connect_data(user_id, payload)
    return result


@router.post("/manual", response_model=dict)
async def manual_sleep_input(
    payload: SleepSessionCreate,
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Manual sleep entry for users who decline Health Connect permission.

    Accepts a single sleep session. Sessions shorter than 5 minutes are
    rejected. Session type is auto-classified (nightly/nap) if not provided.
    Dispatches to Celery storage worker — returns immediately.
    """
    # Reject micro-awakenings / noise
    if payload.duration_mins < 5:
        return {"error": "Session too short (minimum 5 minutes)", "sessions_dispatched": 0}

    # Auto-classify if user did not specify
    session_type = payload.session_type
    if session_type is None:
        start_hour = payload.start_time.hour
        session_type = "nap" if 10 <= start_hour < 18 else "nightly"

    session_dict = {
        "start_time": payload.start_time.isoformat(),
        "end_time": payload.end_time.isoformat(),
        "duration_mins": payload.duration_mins,
        "session_type": session_type,
    }

    insert_sleep_sessions.delay(str(user_id), [session_dict])

    return {"sessions_dispatched": 1, "session_type": session_type}


@router.get("/sessions", response_model=list[SleepSessionResponse])
async def get_sleep_sessions(
    limit: int = 14,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(SleepSession)
        .where(SleepSession.user_id == user_id)
        .order_by(SleepSession.start_time.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/debt", response_model=SleepDebtResponse)
async def get_sleep_debt(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if not user:
        raise ValueError("User not found")

    stmt = (
        select(SleepSession)
        .where(SleepSession.user_id == user_id)
        .order_by(SleepSession.start_time.desc())
        .limit(14)
    )
    result = await db.execute(stmt)
    sessions = result.scalars().all()

    from datetime import datetime, timedelta, timezone
    import numpy as np

    daily: dict[str, float] = {}
    for s in sessions:
        key = s.start_time.strftime("%Y-%m-%d")
        daily[key] = daily.get(key, 0.0) + s.duration_mins

    now = datetime.now(timezone.utc)
    arr = []
    for i in range(14):
        day = now - timedelta(days=13 - i)
        arr.append(daily.get(day.strftime("%Y-%m-%d"), 0.0))

    debt = compute_sleep_debt(user.snop_hours * 60, np.array(arr))

    return SleepDebtResponse(
        user_id=user_id,
        sleep_debt_mins=debt,
        sleep_debt_display=format_sleep_debt(debt),
        snop_hours=user.snop_hours,
    )
