import uuid

from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    email: EmailStr
    chronotype: str  # "Early Bird", "Night Owl", "Neutral"


class LoginRequest(BaseModel):
    email: EmailStr


class AuthResponse(BaseModel):
    user_id: uuid.UUID
    email: str
    chronotype: str


class UserResponse(BaseModel):
    user_id: uuid.UUID
    email: str
    chronotype: str
    snop_hours: float

    class Config:
        from_attributes = True
