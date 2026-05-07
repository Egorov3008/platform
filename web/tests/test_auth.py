import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport, HTTPStatusError, Request, Response
from datetime import datetime, timezone
from app.main import app
from app.core.dependencies import get_conn, get_backend_client
from app.core.security import create_access_token, create_refresh_token
from app.schemas.auth import UserResponse


@pytest.fixture
async def client(mock_conn):
    mock_conn_obj, mock_pool = mock_conn
    async def override_get_conn():
        yield mock_conn_obj
    app.dependency_overrides[get_conn] = override_get_conn
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_me_returns_user_info(client):
    payload = {"sub": "42", "tg_id": 123, "is_admin": False}
    token = create_access_token(payload)
    client.cookies.set("access_token", token)
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == 42
    assert data["tg_id"] == 123
    assert data["is_admin"] is False


@pytest.mark.asyncio
async def test_me_without_cookie_returns_401(client):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_logout_clears_cookies(client):
    resp = await client.post("/api/v1/auth/logout")
    assert resp.status_code == 200
    assert "access_token" in resp.headers.get("set-cookie", "")


@pytest.mark.asyncio
async def test_refresh_with_valid_cookie(client):
    payload = {"sub": "42", "tg_id": 123, "is_admin": False}
    refresh_token = create_refresh_token(payload)
    client.cookies.set("refresh_token", refresh_token)
    resp = await client.post("/api/v1/auth/refresh")
    assert resp.status_code == 200
    assert "access_token" in resp.cookies


@pytest.mark.asyncio
async def test_refresh_without_cookie_returns_401(client):
    resp = await client.post("/api/v1/auth/refresh")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_config_returns_bot_username(client):
    with patch("app.api.auth.settings") as mock_settings:
        mock_settings.telegram_bot_username = "TestVpnBot"
        resp = await client.get("/api/v1/auth/config")
    assert resp.status_code == 200
    assert resp.json()["telegram_bot_username"] == "TestVpnBot"


@pytest.fixture
def mock_backend():
    return AsyncMock()


@pytest.fixture
async def client_with_backend(client, mock_backend):
    async def override():
        return mock_backend
    app.dependency_overrides[get_backend_client] = override
    yield client, mock_backend
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_telegram_callback_new_user(client_with_backend):
    """New user: 404 → create → JWT"""
    client, mock_be = client_with_backend
    mock_be.get_user.side_effect = HTTPStatusError("404", request=Request("GET", "http://t"), response=Response(404))
    mock_be.create_user.return_value = UserResponse(tg_id=123, is_admin=False, balance=0, server_id=1, created_at=datetime.now(timezone.utc))
    with patch("app.api.auth.verify_telegram_data", return_value={"id": 123}), \
         patch("app.api.auth.verify_captcha"), \
         patch("app.services.auth.login_via_telegram", return_value=("access", "refresh")):
        r = await client.post("/api/v1/auth/telegram-callback", json={"telegram_data": {"id": 123, "first_name": "T", "last_name": None, "username": None, "photo_url": None, "auth_date": 1, "hash": "x"}, "captcha_token": "t", "captcha_timestamp": 1, "captcha_answer": 2})
    assert r.status_code == 200
    assert r.json()["user"]["tg_id"] == 123
    mock_be.get_user.assert_called_once_with(123)
    mock_be.create_user.assert_called_once_with(123)


@pytest.mark.asyncio
async def test_telegram_callback_existing_user(client_with_backend):
    """Existing user: 200 → use → JWT"""
    client, mock_be = client_with_backend
    mock_be.get_user.return_value = UserResponse(tg_id=456, is_admin=True, balance=50, server_id=2, created_at=datetime.now(timezone.utc))
    with patch("app.api.auth.verify_telegram_data", return_value={"id": 456}), \
         patch("app.api.auth.verify_captcha"), \
         patch("app.services.auth.login_via_telegram", return_value=("access", "refresh")):
        r = await client.post("/api/v1/auth/telegram-callback", json={"telegram_data": {"id": 456, "first_name": "T", "last_name": None, "username": None, "photo_url": None, "auth_date": 1, "hash": "x"}, "captcha_token": "t", "captcha_timestamp": 1, "captcha_answer": 2})
    assert r.status_code == 200
    mock_be.get_user.assert_called_once_with(456)
    mock_be.create_user.assert_not_called()


@pytest.mark.asyncio
async def test_telegram_callback_backend_error_check(client_with_backend):
    """Backend 5xx on check → 503"""
    client, mock_be = client_with_backend
    mock_be.get_user.side_effect = HTTPStatusError("500", request=Request("GET", "http://t"), response=Response(500))
    with patch("app.api.auth.verify_telegram_data", return_value={"id": 789}), \
         patch("app.api.auth.verify_captcha"):
        r = await client.post("/api/v1/auth/telegram-callback", json={"telegram_data": {"id": 789, "first_name": "T", "last_name": None, "username": None, "photo_url": None, "auth_date": 1, "hash": "x"}, "captcha_token": "t", "captcha_timestamp": 1, "captcha_answer": 2})
    assert r.status_code == 503


@pytest.mark.asyncio
async def test_telegram_callback_backend_error_create(client_with_backend):
    """Backend 5xx on create → 500"""
    client, mock_be = client_with_backend
    mock_be.get_user.side_effect = HTTPStatusError("404", request=Request("GET", "http://t"), response=Response(404))
    mock_be.create_user.side_effect = HTTPStatusError("500", request=Request("POST", "http://t"), response=Response(500))
    with patch("app.api.auth.verify_telegram_data", return_value={"id": 999}), \
         patch("app.api.auth.verify_captcha"):
        r = await client.post("/api/v1/auth/telegram-callback", json={"telegram_data": {"id": 999, "first_name": "T", "last_name": None, "username": None, "photo_url": None, "auth_date": 1, "hash": "x"}, "captcha_token": "t", "captcha_timestamp": 1, "captcha_answer": 2})
    assert r.status_code == 500
