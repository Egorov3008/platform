from typing import Optional, Any
import httpx


class WebBackendClient:
    """HTTP client for communication with backend API.

    All requests include X-Bot-Secret header for authentication.
    Methods include tg_id as query parameter where needed for user-specific endpoints.
    """

    def __init__(self, http_client: httpx.AsyncClient, tg_id: Optional[int], bot_secret: str, admin_api_key: str = ""):
        """Initialize WebBackendClient.

        Args:
            http_client: AsyncClient instance for HTTP requests
            tg_id: Telegram user ID (None for public/unauthenticated endpoints)
            bot_secret: Secret key for X-Bot-Secret header
            admin_api_key: Admin API key for admin operations
        """
        self._client = http_client
        self._tg_id = tg_id
        self._bot_secret = bot_secret
        self._admin_api_key = admin_api_key

    def _get_headers(self) -> dict[str, str]:
        """Get common headers for all requests."""
        return {"X-Bot-Secret": self._bot_secret}

    def _get_params(self) -> dict[str, Any]:
        """Get common query parameters."""
        if self._tg_id is not None:
            return {"tg_id": self._tg_id}
        return {}

    async def list_tariffs(self) -> list[dict]:
        """GET /api/v1/tariffs/ - List all available tariffs."""
        resp = await self._client.get(
            "/api/v1/tariffs/",
            headers=self._get_headers(),
        )
        resp.raise_for_status()
        return resp.json()

    async def get_tariff(self, tariff_id: int) -> dict:
        """GET /api/v1/tariffs/{tariff_id} - Get tariff details."""
        resp = await self._client.get(
            f"/api/v1/tariffs/{tariff_id}",
            headers=self._get_headers(),
        )
        resp.raise_for_status()
        return resp.json()

    async def list_keys(self) -> list[dict]:
        """GET /api/v1/keys?tg_id=... - List user's VPN keys."""
        resp = await self._client.get(
            "/api/v1/keys",
            headers=self._get_headers(),
            params=self._get_params(),
        )
        resp.raise_for_status()
        return resp.json()

    async def get_key(self, email: str) -> dict:
        """GET /api/v1/keys/{email} - Get key details by email."""
        resp = await self._client.get(
            f"/api/v1/keys/{email}",
            headers=self._get_headers(),
        )
        resp.raise_for_status()
        return resp.json()

    async def create_key(self, tariff_id: int) -> dict:
        """POST /api/v1/keys/create - Create a new VPN key."""
        resp = await self._client.post(
            "/api/v1/keys/create",
            headers=self._get_headers(),
            params=self._get_params(),
            json={"tariff_id": tariff_id},
        )
        resp.raise_for_status()
        return resp.json()

    async def delete_key(self, email: str) -> None:
        """DELETE /api/v1/keys/{email} - Delete a VPN key."""
        resp = await self._client.delete(
            f"/api/v1/keys/{email}",
            headers=self._get_headers(),
        )
        resp.raise_for_status()
        # 204 No Content returns None
        if resp.status_code == 204:
            return None
        return resp.json()

    async def renew_key(self, email: str, tg_id: int, tariff_id: int, months: int) -> dict:
        """POST /api/v1/keys/{email}/renew - Renew a VPN key."""
        resp = await self._client.post(
            f"/api/v1/keys/{email}/renew",
            headers=self._get_headers(),
            json={"tg_id": tg_id, "tariff_id": tariff_id, "number_of_months": months},
        )
        resp.raise_for_status()
        return resp.json()

    async def create_payment(self, tariff_id: int, months: int) -> dict:
        """POST /api/v1/payments/create - Create a new payment for VPN key."""
        resp = await self._client.post(
            "/api/v1/payments/create",
            headers=self._get_headers(),
            json={"tg_id": self._tg_id, "tariff_id": tariff_id, "number_of_months": months},
        )
        resp.raise_for_status()
        return resp.json()

    async def create_renewal_payment(self, email: str, tariff_id: int, months: int) -> dict:
        """POST /api/v1/payments/create - Create a renewal payment for existing key."""
        resp = await self._client.post(
            "/api/v1/payments/create",
            headers=self._get_headers(),
            json={"tg_id": self._tg_id, "email": email, "tariff_id": tariff_id, "number_of_months": months, "operation": "renew_key"},
        )
        resp.raise_for_status()
        return resp.json()

    async def get_payment_history(self) -> list[dict]:
        """GET /api/v1/payments?tg_id=... - Get user's payment history."""
        resp = await self._client.get(
            "/api/v1/payments",
            headers=self._get_headers(),
            params=self._get_params(),
        )
        resp.raise_for_status()
        return resp.json()

    async def get_payment_status(self, payment_id: str) -> dict:
        """GET /api/v1/payments/{payment_id}/status - Get payment status."""
        resp = await self._client.get(
            f"/api/v1/payments/{payment_id}/status",
            headers=self._get_headers(),
            params=self._get_params(),
        )
        resp.raise_for_status()
        return resp.json()

    async def get_user(self, tg_id: int) -> dict:
        """GET /api/v1/users/{tg_id} - Get user details."""
        resp = await self._client.get(
            f"/api/v1/users/{tg_id}",
            headers=self._get_headers(),
        )
        resp.raise_for_status()
        return resp.json()
