import uuid
from datetime import datetime

from pydantic import BaseModel


class DeviceTokenRegister(BaseModel):
    """Request to register or update an FCM device token."""
    token: str
    platform: str = "android"


class DeviceTokenResponse(BaseModel):
    """Response for a registered device token."""
    id: uuid.UUID
    token: str
    platform: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
