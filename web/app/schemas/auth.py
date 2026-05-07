from pydantic import BaseModel
from typing import Optional


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
