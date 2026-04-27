from typing import AsyncGenerator, Optional
from fastapi import Depends, HTTPException, Request, status
import asyncpg
import httpx
from app.core.database import get_pool
from app.core.security import decode_token
from app.core.config import settings
from app.api.backend_client import WebBackendClient


async def get_conn() -> AsyncGenerator[asyncpg.Connection, None]:
    try:
        pool = get_pool()
    except RuntimeError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        )
    async with pool.acquire() as conn:
        yield conn


async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = decode_token(token)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    if not payload.get("sub"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    return payload


async def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


# Global backend HTTP client management
_backend_http_client: Optional[httpx.AsyncClient] = None


def set_backend_http_client(client: httpx.AsyncClient) -> None:
    """Set the global backend HTTP client."""
    global _backend_http_client
    _backend_http_client = client


def get_backend_http_client() -> httpx.AsyncClient:
    """Get the global backend HTTP client. Raises RuntimeError if not initialized."""
    if _backend_http_client is None:
        raise RuntimeError("Backend HTTP client not initialized")
    return _backend_http_client


async def get_backend_client(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> WebBackendClient:
    """Get WebBackendClient for authenticated requests.

    Includes tg_id from current_user JWT payload.
    """
    http_client = get_backend_http_client()
    tg_id = current_user.get("tg_id")
    return WebBackendClient(
        http_client=http_client,
        tg_id=tg_id,
        bot_secret=settings.bot_secret_key,
    )


async def get_backend_client_no_auth(
    request: Request,
) -> WebBackendClient:
    """Get WebBackendClient for public/unauthenticated requests.

    Does not include tg_id.
    """
    http_client = get_backend_http_client()
    return WebBackendClient(
        http_client=http_client,
        tg_id=None,
        bot_secret=settings.bot_secret_key,
    )
