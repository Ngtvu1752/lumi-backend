import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, PrimaryKeyConstraint, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Habit(Base):
    """Defines the 16 science-based habits as configurable entities."""
    __tablename__ = "habits"

    habit_id: Mapped[str] = mapped_column(String(50), primary_key=True)  # e.g. "light_exposure"
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    zone_type: Mapped[str] = mapped_column(String(50), nullable=False)  # wake/morning_peak/afternoon_dip/evening_peak/melatonin_window
    default_priority: Mapped[int] = mapped_column(Integer, nullable=False, default=3)  # 1-5, 5=highest
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class UserHabitPreference(Base):
    """User's personal settings for each habit (enable/disable)."""
    __tablename__ = "user_habit_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    habit_id: Mapped[str] = mapped_column(String(50), ForeignKey("habits.habit_id"), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (
        PrimaryKeyConstraint("user_id", "habit_id"),
    )


class HabitLog(Base):
    """Tracks nudge delivery and user engagement per habit."""
    __tablename__ = "habit_logs"

    log_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    habit_id: Mapped[str] = mapped_column(String(50), ForeignKey("habits.habit_id"), nullable=False)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")  # pending/delivered/acknowledged/completed/skipped
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
