import uuid

from pydantic import BaseModel, Field


class SnopUpdateRequest(BaseModel):
    """Manual SNOP override by the user."""
    snop_hours: float = Field(..., ge=4.0, le=12.0, description="Sleep Need for Optimal Performance in hours (4-12)")


class UserResponse(BaseModel):
    user_id: uuid.UUID
    email: str
    chronotype: str
    snop_hours: float

    class Config:
        from_attributes = True
