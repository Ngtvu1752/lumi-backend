import uuid

from fastapi import Header

# Default user UUID for development — bypasses JWT entirely
DEFAULT_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


async def get_current_user_id(x_user_id: str | None = Header(default=None)) -> uuid.UUID:
    """Bypass auth: accept user_id from X-User-Id header, or use default."""
    if x_user_id:
        return uuid.UUID(x_user_id)
    return DEFAULT_USER_ID
