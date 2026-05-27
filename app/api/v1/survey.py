import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.models.survey import UserSurveyResponse
from app.schemas.survey import SurveySubmitRequest, SurveyResponse
from app.services.calibration import calibrate_snop

router = APIRouter(prefix="/survey", tags=["survey"])


@router.post("/submit", response_model=list[SurveyResponse])
async def submit_survey(
    payload: SurveySubmitRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Submit onboarding survey answers (FR-01).

    Triggers SNOP seed calibration after submission.
    """
    responses = []
    for answer in payload.answers:
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
