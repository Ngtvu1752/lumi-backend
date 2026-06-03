import uuid
from datetime import datetime

from pydantic import BaseModel


class HabitResponse(BaseModel):
    habit_id: str
    name: str
    description: str
    zone_type: str
    default_priority: int
    enabled: bool = True  # from user preference (default True if no preference set)

    class Config:
        from_attributes = True


class HabitPreferenceUpdate(BaseModel):
    enabled: bool


class HabitLogCreate(BaseModel):
    habit_id: str
    scheduled_at: datetime
    status: str = "pending"  # pending/delivered/acknowledged/completed/skipped


class HabitLogResponse(BaseModel):
    log_id: uuid.UUID
    habit_id: str
    scheduled_at: datetime
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
