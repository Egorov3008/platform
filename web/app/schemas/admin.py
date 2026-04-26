"""Pydantic-схемы для административных эндпоинтов.

Определяет модели запросов/ответов для управления пользователями
(просмотр, блокировка, назначение администратора) и создания ключей.
"""

from pydantic import BaseModel
from typing import Optional


class UserAdminResponse(BaseModel):
    tg_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    is_admin: bool
    is_blocked: bool
    trial: int
    keys_count: int


class UserPatchRequest(BaseModel):
    is_blocked: Optional[bool] = None
    is_admin: Optional[bool] = None


class AdminCreateKeyRequest(BaseModel):
    tg_id: int
    tariff_id: int
