import uuid
from datetime import datetime

from pydantic import BaseModel


# ── Sound Track ──────────────────────────────────────────────

class SoundTrackResponse(BaseModel):
    sound_id: str
    name: str
    description: str
    category: str
    duration_seconds: int
    file_url: str
    thumbnail_url: str | None = None
    is_favorite: bool = False

    class Config:
        from_attributes = True


class SoundCategoryResponse(BaseModel):
    category: str
    count: int
    sounds: list[SoundTrackResponse]


# ── Favorites ────────────────────────────────────────────────

class FavoriteResponse(BaseModel):
    sound_id: str
    created_at: datetime

    class Config:
        from_attributes = True


# ── Playback Log ─────────────────────────────────────────────

class PlaybackLogCreate(BaseModel):
    sound_id: str
    started_at: datetime
    duration_seconds: int = 0


class PlaybackLogResponse(BaseModel):
    log_id: uuid.UUID
    sound_id: str
    started_at: datetime
    duration_seconds: int
    created_at: datetime

    class Config:
        from_attributes = True


# ── Stats ────────────────────────────────────────────────────

class PlaybackStatsResponse(BaseModel):
    total_listening_minutes: int
    total_sessions: int
    most_played_sound: str | None = None
    favorite_category: str | None = None
