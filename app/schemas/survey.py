import uuid

from pydantic import BaseModel


class SurveyAnswer(BaseModel):
    question_id: str
    answer_key: str


class SurveySubmitRequest(BaseModel):
    answers: list[SurveyAnswer]


class SurveyResponse(BaseModel):
    user_id: uuid.UUID
    question_id: str
    answer_key: str

    class Config:
        from_attributes = True
