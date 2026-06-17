"""
Async HTTP client for VPN platform backend API.

Uses typed DTOs (pydantic models) for type-safe API responses.
Includes circuit breaker for fault tolerance.
"""
from typing import List, Optional

import asyncio
import httpx
import pybreaker

from api.schemas import (
    RegisterFromInviteRequest,
    RegisterFromInviteResponse,
    UserDTO,
    TariffDTO,
    KeyDTO,
    KeyDetailDTO,
    KeyListResponse,
    PaymentDTO,
    PaymentCreateResponse,
    GiftDTO,
    ReferralLinkDTO,
    AdminUserSummaryDTO,
    AdminStatsDTO,
)
from logger import logger




class BackendAPIClient:
    """
    Async HTTP client for VPN platform backend API.

    All methods return typed DTOs (pydantic models) instead of raw dicts,
    providing type safety and better IDE support.

    Circuit breaker pattern protects against cascading failures:
    - Opens after 5 consecutive failures
    - Resets after 30 seconds
    - Half-open state tests 1 request before closing
    """

    def __init__(
        self,
        base_url: str,
        bot_secret: str,
        client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._bot_secret = bot_secret
        self._client = client or httpx.AsyncClient(
            base_url=self._base_url,
            headers={"X-Bot-Secret": bot_secret},
            timeout=10.0,
        )
        self._circuit_breaker = pybreaker.CircuitBreaker(
            fail_max=5,
            reset_timeout=30,
            success_threshold=1,
            name="backend_api_client",
        )

    async def aclose(self) -> None:
        if not self._client.is_closed:
            await self._client.aclose()

    @property
    def circuit_breaker(self) -> pybreaker.CircuitBreaker:
        """Access circuit breaker for monitoring/testing."""
        return self._circuit_breaker

    @staticmethod
    def _unwrap_list(data, key: str):
        """Backend may return a bare list or {"key": [...]}. Normalize to list."""
        if isinstance(data, dict):
            return data.get(key, [])
        return data if isinstance(data, list) else []

    @staticmethod
    def _to_dicts(items):
        """Convert list of Pydantic models (or dicts) to list of dicts.

        Several getters in bot code expect dict[str, Any] for legacy reasons.
        Centralised here so callers don't sprinkle .model_dump() everywhere.
        """
        result = []
        for item in items:
            if isinstance(item, dict):
                result.append(item)
            elif hasattr(item, "model_dump"):
                result.append(item.model_dump())
            else:
                # Pydantic v1 fallback or plain object
                result.append(dict(item) if hasattr(item, "__dict__") else item)
        return result

    async def _request_with_circuit_breaker(self, method: str, path: str, **kwargs) -> httpx.Response:
        """Execute HTTP request with circuit breaker protection."""
        async def _request() -> httpx.Response:
            return await self._client.request(method, f"{self._base_url}{path}", **kwargs)

        return await self._circuit_breaker.call_async(_request)

    # =============================================================================
    # User endpoints
    # =============================================================================

    async def register_user(
        self,
        tg_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        language_code: Optional[str] = None,
        server_id: Optional[int] = None,
    ) -> Optional[UserDTO]:
        """Register a new user. Returns UserDTO or None on error."""
        try:
            r = await self._request_with_circuit_breaker(
                "POST",
                "/api/v1/users/register",
                json={
                    "tg_id": tg_id,
                    "username": username,
                    "first_name": first_name,
                    "last_name": last_name,
                    "language_code": language_code,
                    "server_id": server_id,
                },
            )
            r.raise_for_status()
            return UserDTO(**r.json())
        except pybreaker.CircuitBreakerError:
            logger.error("BackendAPIClient.register_user: circuit breaker open", tg_id=tg_id)
            return None
        except Exception as e:
            logger.error("BackendAPIClient.register_user failed", tg_id=tg_id, error=str(e))
            return None

    async def admin_register_user(self, payload: dict) -> Optional[dict]:
        """Admin endpoint: register a new user (called by bot auto-registration).

        Returns dict with user data on success, None on error.
        """
        try:
            r = await self._request_with_circuit_breaker(
                "POST",
                "/api/v1/admin/users/register",
                json=payload,
            )
            r.raise_for_status()
            return r.json()
        except pybreaker.CircuitBreakerError:
            logger.error("BackendAPIClient.admin_register_user: circuit breaker open", tg_id=payload.get("tg_id"))
            return None
        except Exception as e:
            logger.error("BackendAPIClient.admin_register_user failed", tg_id=payload.get("tg_id"), error=str(e))
            return None

    async def get_user(self, tg_id: int) -> Optional[dict]:
        """
        Fetch user by tg_id (returns dict for legacy callers).

        Returns dict or None if not found / error.
        """
        try:
            r = await self._request_with_circuit_breaker("GET", f"/api/v1/users/{tg_id}")
            if r.status_code == 404:
                return None
            r.raise_for_status()
            data = r.json()
            return data if isinstance(data, dict) else data.model_dump()
        except pybreaker.CircuitBreakerError:
            logger.error("BackendAPIClient.get_user: circuit breaker open", tg_id=tg_id)
            return None
        except Exception as e:
            logger.error("BackendAPIClient.get_user failed", tg_id=tg_id, error=str(e))
            return None

    async def admin_list_users(self) -> List[dict]:
        """List all users for admin panel (returns dicts for legacy callers)."""
        try:
            r = await self._request_with_circuit_breaker("GET", "/api/v1/admin/users")
            r.raise_for_status()
            data = r.json()
            items = self._unwrap_list(data, "users")
            return self._to_dicts(items)
        except pybreaker.CircuitBreakerError:
            logger.error("BackendAPIClient.admin_list_users: circuit breaker open")
            return []
        except Exception as e:
            logger.error("BackendAPIClient.admin_list_users failed", error=str(e))
            return []

    async def admin_update_user(self, tg_id: int, payload: dict) -> Optional[UserDTO]:
        """PATCH /admin/users/{tg_id}. Returns updated user DTO or None."""
        try:
            r = await self._request_with_circuit_breaker("PATCH", f"/api/v1/admin/users/{tg_id}", json=payload)
            r.raise_for_status()
            return UserDTO(**r.json())
        except pybreaker.CircuitBreakerError:
            logger.error("BackendAPIClient.admin_update_user: circuit breaker open", tg_id=tg_id)
            return None
        except Exception as e:
            logger.error("BackendAPIClient.admin_update_user failed", tg_id=tg_id, error=str(e))
            return None

    async def admin_delete_user(self, tg_id: int) -> bool:
        """Delete user by tg_id."""
        try:
            r = await self._request_with_circuit_breaker("POST", f"/api/v1/admin/users/{tg_id}/delete")
            r.raise_for_status()
            return True
        except pybreaker.CircuitBreakerError:
            logger.error("BackendAPIClient.admin_delete_user: circuit breaker open", tg_id=tg_id)
            return False
        except Exception as e:
            logger.error("BackendAPIClient.admin_delete_user failed", tg_id=tg_id, error=str(e))
            return False

    async def get_user_stock(self, tg_id: int) -> Optional[dict]:
        """Returns {"has_discount": bool, "stock_type": str, "value": float} or None."""
        try:
            r = await self._request_with_circuit_breaker("GET", f"/api/v1/admin/users/{tg_id}/stock")
            r.raise_for_status()
            return r.json()
        except pybreaker.CircuitBreakerError:
            logger.error("BackendAPIClient.get_user_stock: circuit breaker open", tg_id=tg_id)
            return None
        except Exception as e:
            logger.error("BackendAPIClient.get_user_stock failed", tg_id=tg_id, error=str(e))
            return None

    # =============================================================================
    # Key endpoints
    # =============================================================================

    async def get_user_keys(self, tg_id: int) -> List[KeyDTO]:
        """Get all keys for a user."""
        try:
            r = await self._request_with_circuit_breaker("GET", "/api/v1/keys/", params={"tg_id": tg_id})
            r.raise_for_status()
            data = r.json()
            # Backend returns a bare list; some endpoints may wrap in {"keys": [...]}
            if isinstance(data, dict):
                items = data.get("keys", [])
            else:
                items = data
            return [KeyDTO(**k) for k in items]
        except pybreaker.CircuitBreakerError:
            logger.error("BackendAPIClient.get_user_keys: circuit breaker open", tg_id=tg_id)
            return []
        except Exception as e:
            logger.error("BackendAPIClient.get_user_keys failed", tg_id=tg_id, error=str(e))
            return []

    async def get_key(self, email: str) -> Optional[KeyDTO]:
        """Get key details by email."""
        try:
            r = await self._request_with_circuit_breaker("GET", f"/api/v1/keys/{email}")
            r.raise_for_status()
            return KeyDTO(**r.json())
        except pybreaker.CircuitBreakerError:
            logger.error("BackendAPIClient.get_key: circuit breaker open", email=email)
            return None
        except Exception as e:
            logger.error("BackendAPIClient.get_key failed", email=email, error=str(e))
            return None

    async def get_key_details(self, email: str) -> Optional[dict]:
        """
        Get full key details (with status fields) by email.

        Hits ``GET /api/v1/keys/{email}`` which returns ``KeyDetailResponse``:
        email, tg_id, expiry_time, key, tariff_id, name_tariff,
        used_traffic, inbound_id, client_id, status_text, days_left,
        hours_left, is_active, is_trial, expiry_date.

        Returns a plain ``dict`` on success so existing getters in
        ``bot/dialogs/`` (which use ``.get()``-style field access) keep
        working without changes — matches the pattern of
        ``get_user()`` / ``admin_list_keys()``.

        Returns ``None`` on 404 / circuit-breaker open / any other error.
        """
        try:
            r = await self._request_with_circuit_breaker("GET", f"/api/v1/keys/{email}")
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r.json()
        except pybreaker.CircuitBreakerError:
            logger.error("BackendAPIClient.get_key_details: circuit breaker open", email=email)
            return None
        except Exception as e:
            logger.error("BackendAPIClient.get_key_details failed", email=email, error=str(e))
            return None

    async def delete_key(self, email: str, tg_id: int) -> bool:
        """Delete key. Returns True on success (204), False on any error."""
        try:
            r = await self._request_with_circuit_breaker(
                "DELETE",
                f"/api/v1/keys/{email}",
                params={"tg_id": tg_id},
            )
            r.raise_for_status()
            return True
        except pybreaker.CircuitBreakerError:
            logger.error("BackendAPIClient.delete_key: circuit breaker open", email=email, tg_id=tg_id)
            return False
        except Exception as e:
            logger.error("BackendAPIClient.delete_key failed", email=email, tg_id=tg_id, error=str(e))
            return False

    async def create_trial_key(self, tg_id: int, gift_token: Optional[str] = None) -> Optional[KeyDTO]:
        """Create trial key for user."""
        try:
            params = {"tg_id": tg_id}
            if gift_token:
                params["gift_token"] = gift_token
            r = await self._request_with_circuit_breaker("POST", "/api/v1/keys/trial", params=params)
            r.raise_for_status()
            return KeyDTO(**r.json())
        except pybreaker.CircuitBreakerError:
            logger.error("BackendAPIClient.create_trial_key: circuit breaker open", tg_id=tg_id)
            return None
        except Exception as e:
            logger.error("BackendAPIClient.create_trial_key failed", tg_id=tg_id, error=str(e))
            return None

    async def admin_list_keys(self) -> List[KeyDTO]:
        """List all keys for admin panel."""
        try:
            r = await self._request_with_circuit_breaker("GET", "/api/v1/admin/keys")
            r.raise_for_status()
            data = r.json()
            return self._to_dicts(self._unwrap_list(data, "keys"))
        except pybreaker.CircuitBreakerError:
            logger.error("BackendAPIClient.admin_list_keys: circuit breaker open")
            return []
        except Exception as e:
            logger.error("BackendAPIClient.admin_list_keys failed", error=str(e))
            return []

    # =============================================================================
    # Tariff endpoints
    # =============================================================================

    async def get_tariff(self, tariff_id: int) -> Optional[TariffDTO]:
        """Get tariff by ID."""
        try:
            r = await self._request_with_circuit_breaker("GET", f"/api/v1/admin/tariffs/{tariff_id}")
            r.raise_for_status()
            return TariffDTO(**r.json())
        except pybreaker.CircuitBreakerError:
            logger.error("BackendAPIClient.get_tariff: circuit breaker open", tariff_id=tariff_id)
            return None
        except Exception as e:
            logger.error("BackendAPIClient.get_tariff failed", tariff_id=tariff_id, error=str(e))
            return None

    async def admin_list_tariffs(self) -> List[TariffDTO]:
        """List all tariffs."""
        try:
            r = await self._request_with_circuit_breaker("GET", "/api/v1/admin/tariffs")
            r.raise_for_status()
            data = r.json()
            return self._to_dicts(self._unwrap_list(data, "tariffs"))
        except pybreaker.CircuitBreakerError:
            logger.error("BackendAPIClient.admin_list_tariffs: circuit breaker open")
            return []
        except Exception as e:
            logger.error("BackendAPIClient.admin_list_tariffs failed", error=str(e))
            return []

    # =============================================================================
    # Payment endpoints
    # =============================================================================

    async def create_payment(
        self,
        tg_id: int,
        tariff_id: int,
        operation: str,
        number_of_months: int = 1,
        email: Optional[str] = None,
        customer_email: Optional[str] = None,
        amount: Optional[float] = None,
    ) -> Optional[PaymentCreateResponse]:
        """
        Create new payment.

        Returns PaymentCreateResponse with confirmation_url or None on error.
        """
        try:
            r = await self._request_with_circuit_breaker(
                "POST",
                "/api/v1/payments/create",
                json={
                    "tg_id": tg_id,
                    "tariff_id": tariff_id,
                    "operation": operation,
                    "number_of_months": number_of_months,
                    "email": email,
                    "customer_email": customer_email,
                    "amount": amount,
                },
            )
            r.raise_for_status()
            return PaymentCreateResponse(**r.json())
        except pybreaker.CircuitBreakerError:
            logger.error("BackendAPIClient.create_payment: circuit breaker open", tg_id=tg_id)
            return None
        except Exception as e:
            logger.error("BackendAPIClient.create_payment failed", tg_id=tg_id, error=str(e))
            return None

    async def get_payment_status(self, payment_id: str, tg_id: int) -> Optional[str]:
        """Get payment status string or None if not found."""
        try:
            r = await self._request_with_circuit_breaker(
                "GET",
                f"/api/v1/payments/{payment_id}/status",
                params={"tg_id": tg_id},
            )
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r.json().get("status")
        except pybreaker.CircuitBreakerError:
            logger.error("BackendAPIClient.get_payment_status: circuit breaker open", payment_id=payment_id)
            return None
        except Exception as e:
            logger.error("BackendAPIClient.get_payment_status failed", payment_id=payment_id, error=str(e))
            return None

    async def admin_list_payments(self) -> List[PaymentDTO]:
        """List all payments for admin panel."""
        try:
            r = await self._request_with_circuit_breaker("GET", "/api/v1/admin/payments")
            r.raise_for_status()
            data = r.json()
            return self._to_dicts(self._unwrap_list(data, "payments"))
        except pybreaker.CircuitBreakerError:
            logger.error("BackendAPIClient.admin_list_payments: circuit breaker open")
            return []
        except Exception as e:
            logger.error("BackendAPIClient.admin_list_payments failed", error=str(e))
            return []

    # =============================================================================
    # Gift endpoints
    # =============================================================================

    async def get_gift_by_token(self, token: str) -> Optional[GiftDTO]:
        """Get gift link by token."""
        try:
            r = await self._request_with_circuit_breaker("GET", f"/api/v1/admin/gifts/{token}")
            r.raise_for_status()
            return GiftDTO(**r.json())
        except pybreaker.CircuitBreakerError:
            logger.error("BackendAPIClient.get_gift_by_token: circuit breaker open", token=token)
            return None
        except Exception as e:
            logger.error("BackendAPIClient.get_gift_by_token failed", token=token, error=str(e))
            return None

    async def admin_list_gifts(self, sender_tg_id: Optional[int] = None) -> List[dict]:
        """List gifts, optionally filtered by sender (returns dicts for legacy callers)."""
        try:
            params = {}
            if sender_tg_id is not None:
                params["sender_tg_id"] = sender_tg_id
            r = await self._request_with_circuit_breaker("GET", "/api/v1/admin/gifts", params=params)
            r.raise_for_status()
            data = r.json()
            return self._to_dicts(self._unwrap_list(data, "gifts"))
        except Exception as e:
            logger.error("BackendAPIClient.admin_list_gifts failed", error=str(e))
            return []

    # =============================================================================
    # Referral endpoints
    # =============================================================================

    async def get_referral_link(self, tg_id: int) -> Optional[ReferralLinkDTO]:
        """Get referral link for user."""
        try:
            r = await self._request_with_circuit_breaker("GET", f"/api/v1/admin/referrals/links/{tg_id}")
            r.raise_for_status()
            return ReferralLinkDTO(**r.json())
        except pybreaker.CircuitBreakerError:
            logger.error("BackendAPIClient.get_referral_link: circuit breaker open", tg_id=tg_id)
            return None
        except Exception as e:
            logger.error("BackendAPIClient.get_referral_link failed", tg_id=tg_id, error=str(e))
            return None

    async def get_referral_stats(self, tg_id: int) -> Optional[dict]:
        """Get referral statistics for user.

        Returns the raw backend dict (``referral_count``, ``rewards_count``,
        ``rewards_total``, ``balance``) so that the dialog getter
        ``dialogs/windows/getters/referral/main.py`` can keep using
        ``dict.get(...)`` semantics. Mismatching field names into a typed
        DTO caused Pydantic validation errors that broke the entire
        referral window.
        """
        try:
            r = await self._request_with_circuit_breaker("GET", f"/api/v1/admin/referrals/stats/{tg_id}")
            r.raise_for_status()
            return r.json()
        except pybreaker.CircuitBreakerError:
            logger.error("BackendAPIClient.get_referral_stats: circuit breaker open", tg_id=tg_id)
            return None
        except Exception as e:
            logger.error("BackendAPIClient.get_referral_stats failed", tg_id=tg_id, error=str(e))
            return None

    async def admin_create_referral_link(self, tg_id: int) -> Optional[ReferralLinkDTO]:
        """Create new referral link for user."""
        try:
            r = await self._request_with_circuit_breaker("POST", "/api/v1/admin/referrals/links", params={"tg_id": tg_id})
            r.raise_for_status()
            return ReferralLinkDTO(**r.json())
        except pybreaker.CircuitBreakerError:
            logger.error("BackendAPIClient.admin_create_referral_link: circuit breaker open", tg_id=tg_id)
            return None
        except Exception as e:
            logger.error("BackendAPIClient.admin_create_referral_link failed", tg_id=tg_id, error=str(e))
            return None

    async def get_referral_link_by_token(self, token: str) -> Optional[ReferralLinkDTO]:
        """Get referral link by token."""
        try:
            r = await self._request_with_circuit_breaker("GET", f"/api/v1/admin/referrals/links/by-token/{token}")
            r.raise_for_status()
            return ReferralLinkDTO(**r.json())
        except pybreaker.CircuitBreakerError:
            logger.error("BackendAPIClient.get_referral_link_by_token: circuit breaker open", token=token)
            return None
        except Exception as e:
            logger.error("BackendAPIClient.get_referral_link_by_token failed", token=token, error=str(e))
            return None

    # =============================================================================
    # Admin endpoints
    # =============================================================================

    async def admin_delete_key(self, email: str) -> bool:
        """Delete key (admin operation)."""
        try:
            r = await self._request_with_circuit_breaker("POST", f"/api/v1/admin/keys/{email}/delete")
            r.raise_for_status()
            return True
        except pybreaker.CircuitBreakerError:
            logger.error("BackendAPIClient.admin_delete_key: circuit breaker open", email=email)
            return False
        except Exception as e:
            logger.error("BackendAPIClient.admin_delete_key failed", email=email, error=str(e))
            return False

    async def admin_generate_key(
        self,
        tg_id: int,
        tariff_id: int,
        server_id: int = 2,
        number_of_months: int = 1,
    ) -> Optional[KeyDTO]:
        """Generate key for user (admin operation)."""
        try:
            r = await self._request_with_circuit_breaker(
                "POST",
                "/api/v1/admin/keys/generate",
                json={
                    "tg_id": tg_id,
                    "tariff_id": tariff_id,
                    "server_id": server_id,
                    "number_of_months": number_of_months,
                },
            )
            r.raise_for_status()
            return KeyDTO(**r.json())
        except pybreaker.CircuitBreakerError:
            logger.error("BackendAPIClient.admin_generate_key: circuit breaker open", tg_id=tg_id)
            return None
        except Exception as e:
            logger.error("BackendAPIClient.admin_generate_key failed", tg_id=tg_id, error=str(e))
            return None

    async def admin_mass_renew(self, emails: List[str], days: int = 30) -> dict:
        """Mass renew keys."""
        try:
            r = await self._request_with_circuit_breaker(
                "POST",
                "/api/v1/admin/keys/mass-renew",
                json={"emails": emails, "days": days},
            )
            r.raise_for_status()
            return r.json()
        except pybreaker.CircuitBreakerError:
            logger.error("BackendAPIClient.admin_mass_renew: circuit breaker open")
            return {"total": len(emails), "success": 0, "failed": len(emails), "results": []}
        except Exception as e:
            logger.error("BackendAPIClient.admin_mass_renew failed", error=str(e))
            return {"total": len(emails), "success": 0, "failed": len(emails), "results": []}

    async def admin_list_inactive_users(self) -> dict:
        """List inactive users."""
        try:
            r = await self._request_with_circuit_breaker("GET", "/api/v1/admin/users/inactive")
            r.raise_for_status()
            return r.json()
        except pybreaker.CircuitBreakerError:
            logger.error("BackendAPIClient.admin_list_inactive_users: circuit breaker open")
            return {"count": 0, "users": []}
        except Exception as e:
            logger.error("BackendAPIClient.admin_list_inactive_users failed", error=str(e))
            return {"count": 0, "users": []}

    async def admin_delete_inactive_users(self) -> dict:
        """Delete inactive users."""
        try:
            r = await self._request_with_circuit_breaker("POST", "/api/v1/admin/users/inactive/delete")
            r.raise_for_status()
            return r.json()
        except pybreaker.CircuitBreakerError:
            logger.error("BackendAPIClient.admin_delete_inactive_users: circuit breaker open")
            return {"deleted": 0}
        except Exception as e:
            logger.error("BackendAPIClient.admin_delete_inactive_users failed", error=str(e))
            return {"deleted": 0}

    async def admin_change_key_date(self, email: str, expiry_time: int) -> bool:
        """Change key expiry date."""
        try:
            r = await self._request_with_circuit_breaker(
                "POST",
                f"/api/v1/admin/keys/{email}/change-date",
                json={"expiry_time": expiry_time},
            )
            r.raise_for_status()
            return True
        except pybreaker.CircuitBreakerError:
            logger.error("BackendAPIClient.admin_change_key_date: circuit breaker open", email=email)
            return False
        except Exception as e:
            logger.error("BackendAPIClient.admin_change_key_date failed", email=email, error=str(e))
            return False

    async def admin_change_key_tariff(self, email: str, tariff_id: int) -> bool:
        """Change key tariff."""
        try:
            r = await self._request_with_circuit_breaker(
                "POST",
                f"/api/v1/admin/keys/{email}/change-tariff",
                json={"tariff_id": tariff_id},
            )
            r.raise_for_status()
            return True
        except pybreaker.CircuitBreakerError:
            logger.error("BackendAPIClient.admin_change_key_tariff: circuit breaker open", email=email)
            return False
        except Exception as e:
            logger.error("BackendAPIClient.admin_change_key_tariff failed", email=email, error=str(e))
            return False

    async def admin_list_inbounds(self) -> List[dict]:
        """List all inbounds."""
        try:
            r = await self._request_with_circuit_breaker("GET", "/api/v1/admin/inbounds")
            r.raise_for_status()
            data = r.json()
            return self._unwrap_list(data, "inbounds")
        except pybreaker.CircuitBreakerError:
            logger.error("BackendAPIClient.admin_list_inbounds: circuit breaker open")
            return []
        except Exception as e:
            logger.error("BackendAPIClient.admin_list_inbounds failed", error=str(e))
            return []

    async def admin_sync(self) -> dict:
        """Trigger manual cache and panel synchronization."""
        try:
            r = await self._request_with_circuit_breaker("POST", "/api/v1/admin/sync", timeout=60.0)
            r.raise_for_status()
            return r.json()
        except pybreaker.CircuitBreakerError:
            logger.error("BackendAPIClient.admin_sync: circuit breaker open")
            return {"status": "error", "error": "circuit breaker open"}
        except Exception as e:
            logger.error("BackendAPIClient.admin_sync failed", error=str(e))
            return {"status": "error", "error": str(e)}

    # =============================================================================
    # Auth from invite (web registration)
    # =============================================================================

    async def register_from_invite(
        self,
        request: RegisterFromInviteRequest,
    ) -> RegisterFromInviteResponse:
        """
        Register new user from web invite.

        Args:
            request: RegisterFromInviteRequest with user data and invite token

        Returns:
            RegisterFromInviteResponse with generated login code

        Raises:
            httpx.HTTPStatusError: If the request fails
        """
        try:
            r = await self._request_with_circuit_breaker(
                "POST",
                "/api/v1/auth/register-from-invite",
                json=request.model_dump(),
            )
            r.raise_for_status()
            return RegisterFromInviteResponse(**r.json())
        except pybreaker.CircuitBreakerError:
            logger.error("BackendAPIClient.register_from_invite: circuit breaker open", tg_id=request.tg_id)
            raise
        except Exception as e:
            logger.error(
                "BackendAPIClient.register_from_invite failed",
                tg_id=request.tg_id,
                error=str(e),
            )
            raise
