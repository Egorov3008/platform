from typing import Optional, Any
import httpx
import logging
import traceback
from httpx import HTTPStatusError
from app.schemas.users import UserResponse

logger = logging.getLogger(__name__)


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

    async def _log_request(self, method: str, path: str, params: Optional[dict] = None, json_data: Optional[dict] = None):
        """Log outgoing request to backend."""
        logger.debug(
            f"Backend request: {method} {path}",
            extra={
                "method": method,
                "path": path,
                "params": params or {},
                "tg_id": self._tg_id,
                "has_json": json_data is not None
            }
        )

    def _log_response(self, method: str, path: str, status_code: int, response_size: int = 0):
        """Log successful response from backend."""
        logger.debug(
            f"Backend response: {method} {path} -> {status_code}",
            extra={
                "method": method,
                "path": path,
                "status_code": status_code,
                "response_size": response_size,
                "tg_id": self._tg_id
            }
        )

    def _log_error(self, method: str, path: str, error: Exception, status_code: Optional[int] = None):
        """Log error response from backend."""
        error_msg = f"Backend error: {method} {path}"
        if status_code:
            error_msg += f" -> {status_code}"

        logger.error(
            error_msg,
            extra={
                "method": method,
                "path": path,
                "status_code": status_code,
                "error_type": type(error).__name__,
                "error": str(error),
                "tg_id": self._tg_id,
                "traceback": traceback.format_exc()
            },
            exc_info=True
        )

    async def list_tariffs(self) -> list[dict]:
        """GET /api/v1/tariffs/ - List all available tariffs."""
        method, path = "GET", "/api/v1/tariffs/"
        try:
            await self._log_request(method, path)
            resp = await self._client.get(
                path,
                headers=self._get_headers(),
            )
            resp.raise_for_status()
            data = resp.json()
            self._log_response(method, path, resp.status_code, len(str(data)))
            return data
        except Exception as e:
            self._log_error(method, path, e, resp.status_code if 'resp' in locals() else None)
            raise

    async def get_tariff(self, tariff_id: int) -> dict:
        """GET /api/v1/tariffs/{tariff_id} - Get tariff details."""
        method, path = "GET", f"/api/v1/tariffs/{tariff_id}"
        try:
            await self._log_request(method, path)
            resp = await self._client.get(path, headers=self._get_headers())
            resp.raise_for_status()
            data = resp.json()
            self._log_response(method, path, resp.status_code, len(str(data)))
            return data
        except Exception as e:
            self._log_error(method, path, e, resp.status_code if 'resp' in locals() else None)
            raise

    async def list_keys(self) -> list[dict]:
        """GET /api/v1/keys?tg_id=... - List user's VPN keys."""
        method, path = "GET", "/api/v1/keys"
        try:
            await self._log_request(method, path, params=self._get_params())
            resp = await self._client.get(
                path,
                headers=self._get_headers(),
                params=self._get_params(),
            )
            resp.raise_for_status()
            data = resp.json()
            self._log_response(method, path, resp.status_code, len(str(data)))
            return data
        except Exception as e:
            self._log_error(method, path, e, resp.status_code if 'resp' in locals() else None)
            raise

    async def get_key(self, email: str) -> dict:
        """GET /api/v1/keys/{email} - Get key details by email."""
        method, path = "GET", f"/api/v1/keys/{email}"
        try:
            await self._log_request(method, path)
            resp = await self._client.get(path, headers=self._get_headers())
            resp.raise_for_status()
            data = resp.json()
            self._log_response(method, path, resp.status_code, len(str(data)))
            return data
        except Exception as e:
            self._log_error(method, path, e, resp.status_code if 'resp' in locals() else None)
            raise

    async def create_key(self, tariff_id: int) -> dict:
        """POST /api/v1/keys/create - Create a new VPN key."""
        method, path = "POST", "/api/v1/keys/create"
        json_data = {"tariff_id": tariff_id}
        try:
            await self._log_request(method, path, params=self._get_params(), json_data=json_data)
            resp = await self._client.post(
                path,
                headers=self._get_headers(),
                params=self._get_params(),
                json=json_data,
            )
            resp.raise_for_status()
            data = resp.json()
            self._log_response(method, path, resp.status_code, len(str(data)))
            return data
        except Exception as e:
            self._log_error(method, path, e, resp.status_code if 'resp' in locals() else None)
            raise

    async def delete_key(self, email: str) -> None:
        """DELETE /api/v1/keys/{email} - Delete a VPN key."""
        method, path = "DELETE", f"/api/v1/keys/{email}"
        try:
            await self._log_request(method, path, params=self._get_params())
            resp = await self._client.delete(path, headers=self._get_headers(), params=self._get_params())
            resp.raise_for_status()
            self._log_response(method, path, resp.status_code)
            if resp.status_code == 204:
                return None
            return resp.json()
        except Exception as e:
            self._log_error(method, path, e, resp.status_code if 'resp' in locals() else None)
            raise

    async def renew_key(self, email: str, tg_id: int, tariff_id: int, months: int) -> dict:
        """POST /api/v1/keys/{email}/renew - Renew a VPN key."""
        method, path = "POST", f"/api/v1/keys/{email}/renew"
        json_data = {"tg_id": tg_id, "tariff_id": tariff_id, "number_of_months": months}
        try:
            await self._log_request(method, path, json_data=json_data)
            resp = await self._client.post(
                path,
                headers=self._get_headers(),
                json=json_data,
            )
            resp.raise_for_status()
            data = resp.json()
            self._log_response(method, path, resp.status_code, len(str(data)))
            return data
        except Exception as e:
            self._log_error(method, path, e, resp.status_code if 'resp' in locals() else None)
            raise

    async def create_payment(self, tariff_id: int, months: int) -> dict:
        """POST /api/v1/payments/create - Create a new payment for VPN key."""
        method, path = "POST", "/api/v1/payments/create"
        json_data = {"tg_id": self._tg_id, "tariff_id": tariff_id, "number_of_months": months}
        try:
            await self._log_request(method, path, json_data=json_data)
            resp = await self._client.post(
                path,
                headers=self._get_headers(),
                json=json_data,
            )
            resp.raise_for_status()
            data = resp.json()
            self._log_response(method, path, resp.status_code, len(str(data)))
            return data
        except Exception as e:
            self._log_error(method, path, e, resp.status_code if 'resp' in locals() else None)
            raise

    async def create_renewal_payment(self, email: str, tariff_id: int, months: int) -> dict:
        """POST /api/v1/payments/create - Create a renewal payment for existing key."""
        method, path = "POST", "/api/v1/payments/create"
        json_data = {"tg_id": self._tg_id, "email": email, "tariff_id": tariff_id, "number_of_months": months, "operation": "renew_key"}
        try:
            await self._log_request(method, path, json_data=json_data)
            resp = await self._client.post(
                path,
                headers=self._get_headers(),
                json=json_data,
            )
            resp.raise_for_status()
            data = resp.json()
            self._log_response(method, path, resp.status_code, len(str(data)))
            return data
        except Exception as e:
            self._log_error(method, path, e, resp.status_code if 'resp' in locals() else None)
            raise

    async def get_payment_history(self) -> list[dict]:
        """GET /api/v1/payments?tg_id=... - Get user's payment history."""
        method, path = "GET", "/api/v1/payments"
        try:
            await self._log_request(method, path, params=self._get_params())
            resp = await self._client.get(
                path,
                headers=self._get_headers(),
                params=self._get_params(),
            )
            resp.raise_for_status()
            data = resp.json()
            self._log_response(method, path, resp.status_code, len(str(data)))
            return data
        except Exception as e:
            self._log_error(method, path, e, resp.status_code if 'resp' in locals() else None)
            raise

    async def get_payment_status(self, payment_id: str) -> dict:
        """GET /api/v1/payments/{payment_id}/status - Get payment status."""
        method, path = "GET", f"/api/v1/payments/{payment_id}/status"
        try:
            await self._log_request(method, path, params=self._get_params())
            resp = await self._client.get(
                path,
                headers=self._get_headers(),
                params=self._get_params(),
            )
            resp.raise_for_status()
            data = resp.json()
            self._log_response(method, path, resp.status_code, len(str(data)))
            return data
        except Exception as e:
            self._log_error(method, path, e, resp.status_code if 'resp' in locals() else None)
            raise

    async def get_user(self, tg_id: int) -> UserResponse:
        """GET /api/v1/users/{tg_id} - Get user details."""
        method, path = "GET", f"/api/v1/users/{tg_id}"
        try:
            await self._log_request(method, path)
            resp = await self._client.get(path, headers=self._get_headers())
            resp.raise_for_status()
            data = resp.json()
            self._log_response(method, path, resp.status_code, len(str(data)))
            return UserResponse(**data)
        except Exception as e:
            self._log_error(method, path, e, resp.status_code if 'resp' in locals() else None)
            raise

    async def create_user(self, tg_id: int) -> UserResponse:
        """POST /api/v1/users/register - Create a new user in backend with minimal data.

        Auto-assigns:
        - server_id (by backend logic)
        - is_admin: false
        - balance: 0.0
        - trial: 0
        """
        method, path = "POST", "/api/v1/users/register"
        json_data = {"tg_id": tg_id}
        try:
            await self._log_request(method, path, json_data=json_data)
            resp = await self._client.post(
                path,
                headers=self._get_headers(),
                json=json_data,
            )
            resp.raise_for_status()
            data = resp.json()
            self._log_response(method, path, resp.status_code, len(str(data)))
            return UserResponse(**data)
        except Exception as e:
            self._log_error(method, path, e, resp.status_code if 'resp' in locals() else None)
            raise
