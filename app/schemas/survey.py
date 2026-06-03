import uuid

from pydantic import BaseModel, Field


class SurveyAnswer(BaseModel):
    question_id: str = Field(..., description="Question identifier (e.g. 'age', 'gender', 'sleep_schedule')")
    answer_key: str = Field(..., min_length=1, description="Answer value (cannot be empty)")


class SurveySubmitRequest(BaseModel):
    """Onboarding survey submission. Must include all required questions:
    - age: user's age (e.g. "25")
    - gender: "M" or "F"
    - sleep_schedule: self-reported sleep need (e.g. "6-7h", "7-8h", "8-9h")
    """
    answers: list[SurveyAnswer] = Field(..., min_length=1)


class SurveyResponse(BaseModel):
    user_id: uuid.UUID
    question_id: str
    answer_key: str

    class Config:
        from_attributes = True
