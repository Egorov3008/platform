"""
DTO schemas for Bot ↔ Backend API communication.

These schemas provide type-safe data transfer between services.
Used by BackendAPIClient for response parsing.
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime


# =============================================================================
# Auth schemas (existing)
# =============================================================================

class RegisterFromInviteRequest(BaseModel):
    """Request to register a new user from web invite"""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "tg_id": 123456789,
            "username": "john_doe",
            "first_name": "John",
            "last_name": "Doe",
            "language_code": "en",
            "invite_token": "web_invite_2026"
        }
    })

    tg_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    language_code: str = "en"
    invite_token: str


class RegisterFromInviteResponse(BaseModel):
    """Response with generated login code"""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "tg_id": 123456789,
            "login_code": "ABC12345",
            "code_expires_at": "2026-04-28T12:34:56Z"
        }
    })

    tg_id: int
    login_code: str = Field(..., pattern=r'^[A-Z0-9]{8}$', description="8-character alphanumeric code")
    code_expires_at: datetime


# =============================================================================
# User DTOs
# =============================================================================

class UserDTO(BaseModel):
    """
    Typed DTO for user data from backend API.

    Replaces Optional[dict] return type in BackendAPIClient.get_user()
    """
    tg_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    language_code: Optional[str] = None
    balance: float = 0.0
    trial: int = 0
    server_id: Optional[int] = None
    is_admin: bool = False
    is_blocked: bool = False
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# =============================================================================
# Tariff DTOs
# =============================================================================

class TariffDTO(BaseModel):
    """
    Typed DTO for tariff data from backend API.

    Replaces Optional[dict] return type in BackendAPIClient.get_tariff()
    """
    id: int
    name_tariff: str
    amount: float
    period: int  # days
    traffic_limit: float  # GB
    limit_ip: int = 3
    description: Optional[str] = None
    is_active: bool = True

    class Config:
        from_attributes = True


# =============================================================================
# Key DTOs
# =============================================================================

class KeyDTO(BaseModel):
    """
    Typed DTO for key data from backend API.

    Replaces Optional[dict] return type in BackendAPIClient.get_key()
    """
    email: str
    tg_id: int
    inbound_id: int
    client_id: str
    key: str
    expiry_time: int  # milliseconds timestamp
    tariff_id: int
    name_tariff: Optional[str] = None
    used_traffic: Optional[float] = None
    public_link: Optional[str] = None
    link_to_connect: Optional[str] = None
    notified_10h: bool = False
    notified_24h: bool = False
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class KeyListResponse(BaseModel):
    """Response for list keys endpoint"""
    keys: List[KeyDTO]
    total: int


class KeyDetailDTO(BaseModel):
    """
    Typed DTO for full key details from backend API.

    Mirrors backend/app/schemas/keys.py::KeyDetailResponse (which extends
    KeyResponse with status fields: days_left, hours_left, is_active, etc.).

    Returned as a dict by ``BackendAPIClient.get_key_details()`` so existing
    getters can keep using ``.get()``-style field access — matches the
    pattern of ``get_user()`` / ``admin_list_keys()``.
    """
    email: str
    tg_id: int
    client_id: str
    expiry_time: int  # milliseconds timestamp
    key: str
    tariff_id: Optional[int] = None
    name_tariff: Optional[str] = None
    used_traffic: Optional[float] = None
    inbound_id: int
    public_link: Optional[str] = None
    link_to_connect: Optional[str] = None
    notified_10h: bool = False
    notified_24h: bool = False
    status_text: str
    days_left: int
    hours_left: int
    is_active: bool
    is_trial: bool
    expiry_date: str

    class Config:
        from_attributes = True


# =============================================================================
# Payment DTOs
# =============================================================================

class PaymentDTO(BaseModel):
    """
    Typed DTO for payment data from backend API.

    Replaces Optional[dict] return type in BackendAPIClient methods
    """
    payment_id: str
    tg_id: int
    amount: float
    payment_type: str  # "create_key|tariff_id" or "renew_key|email"
    status: str  # "pending", "succeeded", "canceled"
    number_of_months: int = 1
    discount_percent: int = 0
    referral_discount: float = 0.0
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PaymentCreateRequest(BaseModel):
    """Request to create a new payment"""
    tg_id: int
    tariff_id: int
    operation: str  # "create_key" or "renew_key"
    number_of_months: int = 1
    email: Optional[str] = None
    customer_email: Optional[str] = None
    amount: Optional[float] = None


class PaymentCreateResponse(BaseModel):
    """Response from create payment endpoint"""
    payment_id: str
    confirmation_url: str
    amount: float


# =============================================================================
# Server DTOs
# =============================================================================

class ServerDTO(BaseModel):
    """Typed DTO for server data"""
    id: int
    server_name: str
    api_url: str
    subscription_url: str
    cluster_name: Optional[str] = None
    is_active: bool = True

    class Config:
        from_attributes = True


# =============================================================================
# Inbound DTOs
# =============================================================================

class InboundDTO(BaseModel):
    """Typed DTO for inbound data"""
    inbound_id: int
    server_id: int
    name_inbound: str
    port: Optional[int] = None
    protocol: Optional[str] = None
    is_active: bool = True

    class Config:
        from_attributes = True


# =============================================================================
# Gift DTOs
# =============================================================================

class GiftDTO(BaseModel):
    """Typed DTO for gift link data"""
    token: str
    sender_tg_id: int
    tariff_id: int
    is_used: bool = False
    used_by_tg_id: Optional[int] = None
    created_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# =============================================================================
# Referral DTOs
# =============================================================================

class ReferralLinkDTO(BaseModel):
    """Typed DTO for referral link data.

    Mirrors the backend response shape returned by
    ``GET/POST /api/v1/admin/referrals/links[...]``. The id-of-the-owner
    field is called ``referrer_tg_id`` on the backend (matching the
    ``referrer_tg_id`` column in the DB and the ``ReferralLink`` dataclass).

    Note: ``token`` is ``Optional`` because
    ``GET /api/v1/admin/referrals/links/{tg_id}`` returns
    ``{"token": null, "referrer_tg_id": tg_id}`` for users who do not
    yet have a referral link (the endpoint signals "no link" via a
    null token rather than HTTP 404). The dialog getter at
    ``dialogs/windows/getters/referral/main.py`` handles the null case
    with ``if link and link.token:``.
    """
    token: Optional[str] = None
    referrer_tg_id: int
    is_active: bool = True
    created_at: Optional[datetime] = None
    id: Optional[int] = None


# =============================================================================
# Admin DTOs
# =============================================================================

class AdminUserSummaryDTO(BaseModel):
    """Summary of user for admin panel"""
    tg_id: int
    username: Optional[str]
    first_name: Optional[str]
    balance: float
    total_keys: int
    total_payments: float
    created_at: datetime
    last_activity: Optional[datetime]


class AdminStatsDTO(BaseModel):
    """Admin dashboard statistics"""
    total_users: int
    active_users: int
    total_keys: int
    active_keys: int
    total_revenue: float
    revenue_today: float
    revenue_week: float
    revenue_month: float
