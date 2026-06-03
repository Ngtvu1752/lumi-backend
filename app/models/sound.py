import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, PrimaryKeyConstraint, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class SoundTrack(Base):
    """Catalog of available sleep sounds (white noise, nature, ambient, etc.)."""
    __tablename__ = "sound_tracks"

    sound_id: Mapped[str] = mapped_column(String(50), primary_key=True)  # e.g. "white_noise"
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    # Categories: white_noise, rain, ocean, nature, ambient, ASMR
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # 0 = infinite loop (mobile app loops the file)
    file_url: Mapped[str] = mapped_column(String(500), nullable=False)
    thumbnail_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class UserSoundFavorite(Base):
    """User's favorite sounds for quick access."""
    __tablename__ = "user_sound_favorites"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    sound_id: Mapped[str] = mapped_column(String(50), ForeignKey("sound_tracks.sound_id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        PrimaryKeyConstraint("user_id", "sound_id"),
    )


class SoundPlaybackLog(Base):
    """Tracks sound playback sessions for analytics."""
    __tablename__ = "sound_playback_logs"

    log_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    sound_id: Mapped[str] = mapped_column(String(50), ForeignKey("sound_tracks.sound_id"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
