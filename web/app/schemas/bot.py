"""Pydantic schemas для Bot API endpoints."""

from pydantic import BaseModel, Field
from typing import Optional


class UserRegisterRequest(BaseModel):
    """Запрос на регистрацию пользователя."""
    tg_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    language_code: Optional[str] = None
    referral_token: Optional[str] = Field(None, description="Token from referral link if user was invited")


class UserResponse(BaseModel):
    """Информация о пользователе."""
    tg_id: int
    username: Optional[str]
    first_name: Optional[str]
    trial: int  # 0 = available, 1 = used
    balance: float  # Referral balance
    is_blocked: bool
    is_admin: bool
    created_at: str


class PriceResult(BaseModel):
    """Результат расчёта цены."""
    original_amount: float
    final_amount: float
    discount_percent: float
    stock_value: float
    stock_type: Optional[str]  # "fix" or "percent"
    has_discount: bool
    volume_discount_applied: bool

    def total(self, months: int) -> float:
        return self.final_amount * months


class TrialKeyRequest(BaseModel):
    """Запрос на создание пробного ключа."""
    tg_id: int


class KeyResponse(BaseModel):
    """Информация о ключе."""
    tg_id: int
    client_id: str
    email: str
    key: str  # Subscription URL
    expiry_time: int  # Epoch ms
    tariff_id: int
    inbound_id: int
    created_at: int


class BotPaymentRequest(BaseModel):
    """Запрос на создание платежа (для бота)."""
    tg_id: int
    tariff_id: int
    months: int = Field(1, ge=1, le=12)
    email: Optional[str] = Field(None, description="Email ключа для продления (если renewal)")


class BotPaymentResponse(BaseModel):
    """Ответ с информацией о платеже."""
    payment_id: str
    payment_url: str
    amount: float  # Final amount to pay
    original_amount: float  # Before discounts
    discount_percent: float
    referral_discount: float


class ReferralLinkResponse(BaseModel):
    """Реферальная ссылка."""
    share_url: str  # Full URL to share with friends
    token: str


class ReferralStatsResponse(BaseModel):
    """Статистика рефералов пользователя."""
    tg_id: int
    referral_count: int
    total_rewards: float
    share_url: str
