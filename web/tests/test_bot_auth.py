import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.dependencies import get_conn
from app.core.config import settings


@pytest.fixture
async def client(mock_conn):
    mock_conn_obj, mock_pool = mock_conn

    async def override_get_conn():
        yield mock_conn_obj

    app.dependency_overrides[get_conn] = override_get_conn
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def set_bot_secret(monkeypatch):
    from app.core import config
    monkeypatch.setattr(config.settings, "bot_secret_key", "test-secret")


@pytest.mark.asyncio
async def test_generate_code_valid_secret(client):
    fake_user = {"id": 1, "tg_id": 123}
    expires_at = datetime(2026, 4, 20, 12, 0, 0, tzinfo=timezone.utc)

    with (
        patch("app.api.bot.users_repo.get_by_tg_id", return_value=fake_user),
        patch("app.api.bot.login_codes_repo.create", return_value=("ABCD1234", expires_at)),
    ):
        resp = await client.post(
            "/api/v1/bot/auth/generate-code",
            json={"tg_id": 123},
            headers={"X-Bot-Secret": "test-secret"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == "ABCD1234"
    assert "expires_at" in data


@pytest.mark.asyncio
async def test_generate_code_wrong_secret(client):
    resp = await client.post(
        "/api/v1/bot/auth/generate-code",
        json={"tg_id": 123},
        headers={"X-Bot-Secret": "wrong-secret"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_generate_code_missing_secret(client):
    resp = await client.post(
        "/api/v1/bot/auth/generate-code",
        json={"tg_id": 123},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_generate_code_unknown_tg_id(client):
    with patch("app.api.bot.users_repo.get_by_tg_id", return_value=None):
        resp = await client.post(
            "/api/v1/bot/auth/generate-code",
            json={"tg_id": 999},
            headers={"X-Bot-Secret": "test-secret"},
        )
    assert resp.status_code == 404
