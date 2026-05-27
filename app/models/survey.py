import uuid

from sqlalchemy import PrimaryKeyConstraint, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class UserSurveyResponse(Base):
    __tablename__ = "user_survey_responses"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    question_id: Mapped[str] = mapped_column(String(50), nullable=False)
    answer_key: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("user_id", "question_id"),
    )
