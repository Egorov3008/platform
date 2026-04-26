from dataclasses import dataclass
from typing import List, Optional

import httpx

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

    async def get_user(self, tg_id: int) -> Optional[BackendUser]:
        try:
            r = await self._client.get(f"/api/v1/users/{tg_id}")
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return BackendUser.from_dict(r.json())
        except Exception as e:
            logger.error("BackendAPIClient.get_user failed", tg_id=tg_id, error=str(e))
            return None

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
