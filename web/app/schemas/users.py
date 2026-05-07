"""User-related Pydantic schemas."""

from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class UserResponse(BaseModel):
    """User data returned from backend /users endpoint"""
    tg_id: int
    is_admin: bool
    balance: float = 0.0
    server_id: Optional[int] = None
    created_at: datetime
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    language_code: Optional[str] = None
    is_bot: bool = False
    is_blocked: bool = False
    trial: int = 0
    referral_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)
