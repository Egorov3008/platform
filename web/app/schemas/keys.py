"""Pydantic-схемы для эндпоинтов управления ключами.

Содержит модели ответа с информацией о ключе (трафик, тариф, срок)
и запросы на создание/продление.
"""

from pydantic import BaseModel
from typing import Optional


class KeyResponse(BaseModel):
    client_id: str
    email: str
    key: str
    expiry_time: int
    tariff_id: Optional[int] = None
    name_tariff: Optional[str] = None
    amount: Optional[float] = None
    period: Optional[int] = None
    used_traffic: Optional[float] = None


class CreateKeyRequest(BaseModel):
    tariff_id: int


class RenewKeyRequest(BaseModel):
    tariff_id: int
