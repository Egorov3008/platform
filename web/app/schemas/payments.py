"""Pydantic-схемы для эндпоинтов платежей.

Определяет запрос на создание платежа (tariff_id) и ответ со ссылкой
на оплату.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class CreatePaymentRequest(BaseModel):
    tariff_id: int


class PaymentResponse(BaseModel):
    payment_id: str
    payment_url: str
    amount: float


class RenewPaymentRequest(BaseModel):
    client_id: str
    tariff_id: int


class PaymentHistoryItem(BaseModel):
    payment_id: str
    amount: float
    status: str
    payment_type: Optional[str] = None
    created_at: datetime


class PaymentStatusResponse(BaseModel):
    payment_id: str
    status: str
    processed: bool
