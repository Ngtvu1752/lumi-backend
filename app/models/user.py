import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Double, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    chronotype: Mapped[str] = mapped_column(String(50), nullable=False)
    snop_hours: Mapped[float] = mapped_column(Double, nullable=False, default=8.0)
    current_sleep_debt: Mapped[float] = mapped_column(Double, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
