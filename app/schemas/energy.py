import uuid
from datetime import datetime

from pydantic import BaseModel


class EnergyPoint(BaseModel):
    time: datetime
    value: float


class EnergyZone(BaseModel):
    zone_type: str  # "wake", "morning_peak", "afternoon_dip", "evening_peak", "melatonin_window"
    start_time: datetime
    end_time: datetime


class NudgeEvent(BaseModel):
    time: datetime
    message: str
    nudge_type: str  # light_exposure, hydration, exercise, deep_work, caffeine, caffeine_cutoff,
    # meal_timing, nap, task_suggestion, blue_light, wind_down


class EnergyScheduleResponse(BaseModel):
    user_id: uuid.UUID
    date: datetime
    energy_points: list[EnergyPoint]
    zones: list[EnergyZone]
    nudges: list[NudgeEvent]
    is_cached: bool = False
