from pydantic import BaseModel
from typing import Optional


class LoginCodeRequest(BaseModel):
    code: str = "пароль из телеграмм бота" 


class UserInfoResponse(BaseModel):
    id: int
    tg_id: Optional[int] = None
    is_admin: bool


class GenerateCodeRequest(BaseModel):
    tg_id: int


class GenerateCodeResponse(BaseModel):
    code: str
    expires_at: str
