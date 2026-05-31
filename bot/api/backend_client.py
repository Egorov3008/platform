from dataclasses import dataclass
from typing import List, Optional

import httpx

from api.schemas import RegisterFromInviteRequest, RegisterFromInviteResponse
from logger import logger


@dataclass
class BackendUser:
    tg_id: int
    username: Optional[str]
    first_name: Optional[str]
    balance: float
    trial: int
    server_id: Optional[int]
    is_admin: bool
    is_blocked: bool

    @classmethod
    def from_dict(cls, d: dict) -> "BackendUser":
        return cls(
            tg_id=d["tg_id"],
            username=d.get("username"),
            first_name=d.get("first_name"),
            balance=d.get("balance", 0.0),
            trial=d.get("trial", 0),
            server_id=d.get("server_id"),
            is_admin=d.get("is_admin", False),
            is_blocked=d.get("is_blocked", False),
        )


@dataclass
class BackendKey:
    email: str
    tg_id: int
    expiry_time: int
    key: str
    inbound_id: int
    tariff_id: Optional[int] = None
    name_tariff: Optional[str] = None
    total_gb: Optional[int] = None
    used_traffic: Optional[float] = None
    public_link: Optional[str] = None
    link_to_connect: Optional[str] = None
    notified_10h: bool = False
    notified_24h: bool = False

    @classmethod
    def from_dict(cls, d: dict) -> "BackendKey":
        return cls(
            email=d["email"],
            tg_id=d["tg_id"],
            expiry_time=d["expiry_time"],
            key=d["key"],
            inbound_id=d["inbound_id"],
            tariff_id=d.get("tariff_id"),
            name_tariff=d.get("name_tariff"),
            total_gb=d.get("total_gb"),
            used_traffic=d.get("used_traffic"),
            public_link=d.get("public_link"),
            link_to_connect=d.get("link_to_connect"),
            notified_10h=d.get("notified_10h", False),
            notified_24h=d.get("notified_24h", False),
        )


class BackendAPIClient:
    """Async HTTP client for VPN platform backend API."""

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

    async def aclose(self) -> None:
        if not self._client.is_closed:
            await self._client.aclose()

    async def register_user(
        self,
        tg_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        language_code: Optional[str] = None,
        server_id: Optional[int] = None,
    ) -> Optional[BackendUser]:
        try:
            r = await self._client.post(
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
            return BackendUser.from_dict(r.json())
        except Exception as e:
            logger.error("BackendAPIClient.register_user failed", tg_id=tg_id, error=str(e))
            return None

    async def get_user_keys(self, tg_id: int) -> List[BackendKey]:
        try:
            r = await self._client.get("/api/v1/keys/", params={"tg_id": tg_id})
            r.raise_for_status()
            return [BackendKey.from_dict(k) for k in r.json()]
        except Exception as e:
            logger.error("BackendAPIClient.get_user_keys failed", tg_id=tg_id, error=str(e))
            return []

    async def get_key_details(self, email: str) -> Optional[dict]:
        try:
            r = await self._client.get(f"/api/v1/keys/{email}")
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error("BackendAPIClient.get_key_details failed", email=email, error=str(e))
            return None

    async def delete_key(self, email: str, tg_id: int) -> bool:
        """Returns True on success (204), False on any error."""
        try:
            r = await self._client.delete(
                f"/api/v1/keys/{email}",
                params={"tg_id": tg_id},
            )
            r.raise_for_status()
            return True
        except Exception as e:
            logger.error("BackendAPIClient.delete_key failed", email=email, tg_id=tg_id, error=str(e))
            return False

    async def create_payment(
        self,
        tg_id: int,
        tariff_id: int,
        operation: str,
        number_of_months: int = 1,
        email: Optional[str] = None,
        customer_email: Optional[str] = None,
        amount: Optional[float] = None,
    ) -> Optional[dict]:
        """Returns {"payment_id": ..., "confirmation_url": ..., "amount": ...} or None."""
        try:
            r = await self._client.post(
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
            return r.json()
        except Exception as e:
            logger.error("BackendAPIClient.create_payment failed", tg_id=tg_id, error=str(e))
            return None

    async def get_payment_status(self, payment_id: str, tg_id: int) -> Optional[str]:
        """Returns status string ("pending"/"succeeded"/"canceled") or None if not found."""
        try:
            r = await self._client.get(
                f"/api/v1/payments/{payment_id}/status",
                params={"tg_id": tg_id},
            )
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r.json().get("status")
        except Exception as e:
            logger.error("BackendAPIClient.get_payment_status failed", payment_id=payment_id, error=str(e))
            return None

    async def admin_delete_key(self, email: str) -> bool:
        try:
            r = await self._client.post(f"/api/v1/admin/keys/{email}/delete")
            r.raise_for_status()
            return True
        except Exception as e:
            logger.error("BackendAPIClient.admin_delete_key failed", email=email, error=str(e))
            return False

    async def admin_generate_key(
        self,
        tg_id: int,
        tariff_id: int,
        server_id: int = 2,
        number_of_months: int = 1,
    ) -> Optional[dict]:
        try:
            r = await self._client.post(
                "/api/v1/admin/keys/generate",
                json={
                    "tg_id": tg_id,
                    "tariff_id": tariff_id,
                    "server_id": server_id,
                    "number_of_months": number_of_months,
                },
            )
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error("BackendAPIClient.admin_generate_key failed", tg_id=tg_id, error=str(e))
            return None

    async def admin_mass_renew(self, emails: List[str], days: int = 30) -> dict:
        try:
            r = await self._client.post(
                "/api/v1/admin/keys/mass-renew",
                json={"emails": emails, "days": days},
            )
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error("BackendAPIClient.admin_mass_renew failed", error=str(e))
            return {"total": len(emails), "success": 0, "failed": len(emails), "results": []}

    async def admin_list_inactive_users(self) -> dict:
        try:
            r = await self._client.get("/api/v1/admin/users/inactive")
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error("BackendAPIClient.admin_list_inactive_users failed", error=str(e))
            return {"count": 0, "users": []}

    async def admin_delete_inactive_users(self) -> dict:
        try:
            r = await self._client.post("/api/v1/admin/users/inactive/delete")
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error("BackendAPIClient.admin_delete_inactive_users failed", error=str(e))
            return {"deleted": 0}

    async def admin_change_key_date(self, email: str, expiry_time: int) -> bool:
        try:
            r = await self._client.post(
                f"/api/v1/admin/keys/{email}/change-date",
                json={"expiry_time": expiry_time},
            )
            r.raise_for_status()
            return True
        except Exception as e:
            logger.error("BackendAPIClient.admin_change_key_date failed", email=email, error=str(e))
            return False

    async def admin_change_key_tariff(self, email: str, tariff_id: int) -> bool:
        try:
            r = await self._client.post(
                f"/api/v1/admin/keys/{email}/change-tariff",
                json={"tariff_id": tariff_id},
            )
            r.raise_for_status()
            return True
        except Exception as e:
            logger.error("BackendAPIClient.admin_change_key_tariff failed", email=email, error=str(e))
            return False

    async def admin_delete_user(self, tg_id: int) -> bool:
        try:
            r = await self._client.post(f"/api/v1/admin/users/{tg_id}/delete")
            r.raise_for_status()
            return True
        except Exception as e:
            logger.error("BackendAPIClient.admin_delete_user failed", tg_id=tg_id, error=str(e))
            return False

    async def admin_list_inbounds(self) -> List[dict]:
        try:
            r = await self._client.get("/api/v1/admin/inbounds")
            r.raise_for_status()
            data = r.json()
            return data.get("inbounds", [])
        except Exception as e:
            logger.error("BackendAPIClient.admin_list_inbounds failed", error=str(e))
            return []

    async def admin_list_tariffs(self) -> List[dict]:
        try:
            r = await self._client.get("/api/v1/admin/tariffs")
            r.raise_for_status()
            data = r.json()
            return data.get("tariffs", [])
        except Exception as e:
            logger.error("BackendAPIClient.admin_list_tariffs failed", error=str(e))
            return []

    async def get_tariff(self, tariff_id: int) -> Optional[dict]:
        try:
            r = await self._client.get(f"/api/v1/admin/tariffs/{tariff_id}")
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error("BackendAPIClient.get_tariff failed", tariff_id=tariff_id, error=str(e))
            return None

    async def get_key(self, email: str) -> Optional[BackendKey]:
        try:
            r = await self._client.get(f"/api/v1/keys/{email}")
            r.raise_for_status()
            data = r.json()
            return BackendKey.from_dict(data)
        except Exception as e:
            logger.error("BackendAPIClient.get_key failed", email=email, error=str(e))
            return None

    async def get_user(self, tg_id: int) -> Optional[dict]:
        try:
            r = await self._client.get(f"/api/v1/admin/users/{tg_id}")
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error("BackendAPIClient.get_user failed", tg_id=tg_id, error=str(e))
            return None

    async def admin_register_user(self, payload: dict) -> dict:
        try:
            r = await self._client.post("/api/v1/admin/users/register", json=payload)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error("BackendAPIClient.admin_register_user failed", error=str(e))
            return {}

    async def get_gift_by_token(self, token: str) -> Optional[dict]:
        try:
            r = await self._client.get(f"/api/v1/admin/gifts/{token}")
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error("BackendAPIClient.get_gift_by_token failed", token=token, error=str(e))
            return None

    async def admin_list_gifts(self, sender_tg_id: Optional[int] = None) -> List[dict]:
        try:
            params = {}
            if sender_tg_id is not None:
                params["sender_tg_id"] = sender_tg_id
            r = await self._client.get("/api/v1/admin/gifts", params=params)
            r.raise_for_status()
            data = r.json()
            return data.get("gifts", [])
        except Exception as e:
            logger.error("BackendAPIClient.admin_list_gifts failed", error=str(e))
            return []

    async def create_trial_key(self, tg_id: int, gift_token: Optional[str] = None) -> Optional[BackendKey]:
        try:
            params = {"tg_id": tg_id}
            if gift_token:
                params["gift_token"] = gift_token
            r = await self._client.post("/api/v1/keys/trial", params=params)
            r.raise_for_status()
            data = r.json()
            return BackendKey.from_dict(data)
        except Exception as e:
            logger.error("BackendAPIClient.create_trial_key failed", tg_id=tg_id, error=str(e))
            return None

    async def admin_list_keys(self) -> List[BackendKey]:
        try:
            r = await self._client.get("/api/v1/admin/keys")
            r.raise_for_status()
            data = r.json()
            return [BackendKey.from_dict(k) for k in data.get("keys", [])]
        except Exception as e:
            logger.error("BackendAPIClient.admin_list_keys failed", error=str(e))
            return []

    async def admin_list_payments(self) -> List[dict]:
        try:
            r = await self._client.get("/api/v1/admin/payments")
            r.raise_for_status()
            data = r.json()
            return data.get("payments", [])
        except Exception as e:
            logger.error("BackendAPIClient.admin_list_payments failed", error=str(e))
            return []

    async def get_referral_link(self, tg_id: int) -> Optional[dict]:
        try:
            r = await self._client.get(f"/api/v1/admin/referrals/links/{tg_id}")
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error("BackendAPIClient.get_referral_link failed", tg_id=tg_id, error=str(e))
            return None

    async def get_referral_stats(self, tg_id: int) -> Optional[dict]:
        try:
            r = await self._client.get(f"/api/v1/admin/referrals/stats/{tg_id}")
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error("BackendAPIClient.get_referral_stats failed", tg_id=tg_id, error=str(e))
            return None

    async def admin_create_referral_link(self, tg_id: int) -> Optional[dict]:
        try:
            r = await self._client.post("/api/v1/admin/referrals/links", params={"tg_id": tg_id})
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error("BackendAPIClient.admin_create_referral_link failed", tg_id=tg_id, error=str(e))
            return None

    async def get_referral_link_by_token(self, token: str) -> Optional[dict]:
        try:
            r = await self._client.get(f"/api/v1/admin/referrals/links/by-token/{token}")
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error("BackendAPIClient.get_referral_link_by_token failed", token=token, error=str(e))
            return None

    async def admin_list_users(self) -> List[dict]:
        try:
            r = await self._client.get("/api/v1/admin/users")
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error("BackendAPIClient.admin_list_users failed", error=str(e))
            return []

    async def admin_update_user(self, tg_id: int, payload: dict) -> Optional[dict]:
        """PATCH /admin/users/{tg_id}. Returns updated user dict or None."""
        try:
            r = await self._client.patch(f"/api/v1/admin/users/{tg_id}", json=payload)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error("BackendAPIClient.admin_update_user failed", tg_id=tg_id, error=str(e))
            return None

    async def get_user_stock(self, tg_id: int) -> Optional[dict]:
        """Returns {"has_discount": bool, "stock_type": str, "value": float} or None."""
        try:
            r = await self._client.get(f"/api/v1/admin/users/{tg_id}/stock")
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error("BackendAPIClient.get_user_stock failed", tg_id=tg_id, error=str(e))
            return None

    async def admin_sync(self) -> dict:
        """Trigger manual cache and panel synchronization. Returns full result dict."""
        try:
            r = await self._client.post("/api/v1/admin/sync")
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error("BackendAPIClient.admin_sync failed", error=str(e))
            return {"status": "error", "error": str(e)}

    async def register_from_invite(
        self, request: RegisterFromInviteRequest
    ) -> RegisterFromInviteResponse:
        """Register new user from web invite.

        Args:
            request: RegisterFromInviteRequest with user data and invite token

        Returns:
            RegisterFromInviteResponse with generated login code

        Raises:
            httpx.HTTPStatusError: If the request fails
        """
        try:
            r = await self._client.post(
                "/api/v1/auth/register-from-invite",
                json=request.model_dump(),
            )
            r.raise_for_status()
            return RegisterFromInviteResponse(**r.json())
        except Exception as e:
            logger.error(
                "BackendAPIClient.register_from_invite failed",
                tg_id=request.tg_id,
                error=str(e),
            )
            raise
