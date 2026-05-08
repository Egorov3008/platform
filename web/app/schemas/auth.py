from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class LoginCodeRequest(BaseModel):
    code: str


class TelegramOnlyRequest(BaseModel):
    telegram_data: "TelegramAuthData"


class UserInfoResponse(BaseModel):
    id: int
    tg_id: Optional[int] = None
    is_admin: bool


class TelegramAuthData(BaseModel):
    id: int
    first_name: str
    last_name: str | None = None
    username: str | None = None
    photo_url: str | None = None
    auth_date: int
    hash: str


class TelegramCallbackRequest(BaseModel):
    telegram_data: TelegramAuthData
    captcha_token: str
    captcha_timestamp: int
    captcha_answer: int


class CaptchaResponse(BaseModel):
    question: str
    token: str
    timestamp: int


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
