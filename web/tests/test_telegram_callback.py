"""Тесты для login_via_telegram (Task 5) и API-эндпоинтов /captcha + /telegram-callback (Task 6)."""

import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.dependencies import get_backend_http_client, get_conn
from app.services.auth import login_via_telegram


# ---------------- Task 5: login_via_telegram ----------------


@pytest.mark.asyncio
async def test_login_via_telegram_new_user():
    """Если web_users не найден по tg_id, создаётся новая запись с email tg_<id>@bot.local."""
    conn = AsyncMock()
    new_user = {"id": 101, "tg_id": 555, "email": "tg_555@bot.local"}

    with (
        patch("app.services.auth.web_users_repo.get_by_tg_id", return_value=None),
        patch("app.services.auth.web_users_repo.create", return_value=new_user) as mock_create,
    ):
        access_token, refresh_token = await login_via_telegram(conn, tg_id=555, is_admin=False)

    mock_create.assert_called_once()
    call_kwargs = mock_create.call_args[1]
    assert call_kwargs["email"] == "tg_555@bot.local"
    assert call_kwargs["tg_id"] == 555
    assert call_kwargs["password_hash"]  # должен быть рандомный hash
    assert access_token
    assert refresh_token


@pytest.mark.asyncio
async def test_login_via_telegram_existing_user():
    """Если web_users уже существует, токены выпускаются без вызова create."""
    conn = AsyncMock()
    existing_user = {"id": 77, "tg_id": 999, "email": "tg_999@bot.local"}

    with (
        patch("app.services.auth.web_users_repo.get_by_tg_id", return_value=existing_user),
        patch("app.services.auth.web_users_repo.create") as mock_create,
    ):
        access_token, refresh_token = await login_via_telegram(conn, tg_id=999, is_admin=True)

    mock_create.assert_not_called()
    assert access_token
    assert refresh_token


# ---------------- Task 6: GET /captcha + POST /telegram-callback ----------------


@pytest.fixture
async def client(mock_conn):
    """HTTP-клиент с mock asyncpg-соединением и mock backend http_client."""
    mock_conn_obj, _mock_pool = mock_conn

    async def override_get_conn():
        yield mock_conn_obj

    mock_http_client = AsyncMock()

    def override_get_backend_http_client():
        return mock_http_client

    app.dependency_overrides[get_conn] = override_get_conn
    app.dependency_overrides[get_backend_http_client] = override_get_backend_http_client
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        c.mock_http_client = mock_http_client
        yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_captcha(client):
    """GET /api/v1/auth/captcha возвращает question/token/timestamp с арифметической задачей."""
    resp = await client.get("/api/v1/auth/captcha")

    assert resp.status_code == 200
    data = resp.json()
    assert "question" in data
    assert "token" in data
    assert "timestamp" in data
    assert "+" in data["question"]
    assert isinstance(data["timestamp"], int)
    assert isinstance(data["token"], str) and len(data["token"]) > 0


@pytest.mark.asyncio
async def test_telegram_callback_wrong_captcha(client):
    """POST /api/v1/auth/telegram-callback возвращает 400, если capcha-токен неверный."""
    payload = {
        "telegram_data": {
            "id": 12345,
            "first_name": "Test",
            "auth_date": 1714290000,
            "hash": "deadbeef",
        },
        "captcha_token": "invalid-token-not-matching-hmac",
        "captcha_timestamp": 9999999999,
        "captcha_answer": 42,
    }

    resp = await client.post("/api/v1/auth/telegram-callback", json=payload)

    assert resp.status_code == 400
    assert "captcha" in resp.json()["detail"].lower()
