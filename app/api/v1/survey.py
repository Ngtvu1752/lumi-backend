import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id
from app.core.exceptions import ValidationError
from app.db.session import get_db
from app.models.survey import UserSurveyResponse
from app.schemas.survey import SurveySubmitRequest, SurveyResponse
from app.services.calibration import calibrate_snop

router = APIRouter(prefix="/survey", tags=["survey"])

# Core questions required for SNOP seed calibration (calibration.py:_seed_from_survey)
REQUIRED_QUESTIONS = {"age", "gender", "sleep_schedule"}


@router.post("/submit", response_model=list[SurveyResponse])
async def submit_survey(
    payload: SurveySubmitRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Submit onboarding survey answers (FR-01).

    Validates that all required questions are present before saving.
    Triggers SNOP seed calibration after submission.

    Required questions: age, gender, sleep_schedule
    """
    # Validate required questions
    submitted_ids = {answer.question_id for answer in payload.answers}
    missing = REQUIRED_QUESTIONS - submitted_ids
    if missing:
        raise ValidationError(
            f"Missing required survey questions: {', '.join(sorted(missing))}. "
            f"All of {sorted(REQUIRED_QUESTIONS)} must be provided."
        )

    # Validate answer values are not empty
    for answer in payload.answers:
        if not answer.answer_key or not answer.answer_key.strip():
            raise ValidationError(
                f"Answer for '{answer.question_id}' cannot be empty."
            )

    # Upsert: update existing answers or insert new ones
    existing_stmt = select(UserSurveyResponse).where(UserSurveyResponse.user_id == user_id)
    existing_result = await db.execute(existing_stmt)
    existing_map = {r.question_id: r for r in existing_result.scalars().all()}

    responses = []
    for answer in payload.answers:
        if answer.question_id in existing_map:
            # Update existing answer
            existing_map[answer.question_id].answer_key = answer.answer_key
            responses.append(existing_map[answer.question_id])
        else:
            # Insert new answer
            resp = UserSurveyResponse(
                user_id=user_id,
                question_id=answer.question_id,
                answer_key=answer.answer_key,
            )
            db.add(resp)
            responses.append(resp)

    await db.flush()

    # Calibrate SNOP from seed data
    await calibrate_snop(db, user_id)

    return responses
