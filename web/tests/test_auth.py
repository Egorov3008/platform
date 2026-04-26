import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.dependencies import get_conn
from app.core.security import create_access_token, create_refresh_token


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
async def test_login_with_valid_code_sets_cookies(client):
    fake_record = {"id": 1, "code": "ABCD1234", "tg_id": 123, "used": True}
    fake_user = {"id": 42, "tg_id": 123, "email": "tg_123@bot.local"}

    with (
        patch("app.services.auth.login_codes_repo.consume", return_value=fake_record),
        patch("app.services.auth.web_users_repo.get_by_tg_id", return_value=fake_user),
    ):
        resp = await client.post("/api/v1/auth/login", json={"code": "ABCD1234"})

    assert resp.status_code == 200
    assert "access_token" in resp.cookies
    assert "refresh_token" in resp.cookies
    assert "csrf_token" in resp.cookies


@pytest.mark.asyncio
async def test_login_with_invalid_code_returns_400(client):
    with patch("app.services.auth.login_codes_repo.consume", return_value=None):
        resp = await client.post("/api/v1/auth/login", json={"code": "BADCODE1"})

    assert resp.status_code == 400


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
