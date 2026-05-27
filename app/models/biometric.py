import uuid
from datetime import datetime

from sqlalchemy import DateTime, Double, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class BiometricData(Base):
    __tablename__ = "biometric_data"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, primary_key=True)
    metric_type: Mapped[str] = mapped_column(String(50), nullable=False)  # heart_rate_bpm, sleep_stage_rem, etc.
    value: Mapped[float] = mapped_column(Double, nullable=False)
