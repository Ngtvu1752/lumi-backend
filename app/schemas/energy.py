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
    nudge_type: str  # light_exposure, morning_hydration, morning_stretch, deep_work, morning_exercise,
    # strategic_caffeine, caffeine_cutoff, meal_timing, hydration_taper, power_nap,
    # passive_tasks, afternoon_walk, evening_exercise, social_creative, blue_light, wind_down
    priority: int = 3  # 1-5, 5 = highest priority (adapted based on sleep debt)


class EnergyScheduleResponse(BaseModel):
    user_id: uuid.UUID
    date: datetime
    energy_points: list[EnergyPoint]
    zones: list[EnergyZone]
    nudges: list[NudgeEvent]
    energy_potential: float = 0.0  # 0-100, higher = more peak energy available
    is_cached: bool = False
