import uuid
from datetime import datetime

from pydantic import BaseModel


class SleepSessionCreate(BaseModel):
    start_time: datetime
    end_time: datetime
    duration_mins: int
    session_type: str | None = None  # "nightly" or "nap" — auto-classified if omitted


class SleepSessionResponse(BaseModel):
    session_id: uuid.UUID
    user_id: uuid.UUID
    start_time: datetime
    end_time: datetime
    duration_mins: int
    session_type: str

    class Config:
        from_attributes = True


class SleepDebtResponse(BaseModel):
    user_id: uuid.UUID
    sleep_debt_mins: float
    sleep_debt_display: str  # e.g. "4h 30m"
    snop_hours: float
    window_days: int = 14


class HealthConnectSyncRequest(BaseModel):
    """Payload from Android Health Connect sync."""
    sleep_sessions: list[SleepSessionCreate]
    heart_rate_records: list[dict] | None = None
    steps_records: list[dict] | None = None
