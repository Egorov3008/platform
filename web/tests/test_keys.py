"""Тесты эндпоинтов управления ключами.

Проверяют авторизацию, обработку ключей через backend API.
Мокируют WebBackendClient для тестирования функциональности.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.dependencies import get_current_user, get_backend_client
from app.core.security import create_access_token
from app.api.backend_client import WebBackendClient


def make_auth_token(tg_id=None):
    return create_access_token({"sub": "1", "tg_id": tg_id, "is_admin": False})


@pytest.fixture
async def client():
    """Test client with mocked backend."""
    mock_backend = AsyncMock(spec=WebBackendClient)

    async def override_get_backend_client(request=None, current_user=None):
        return mock_backend

    app.dependency_overrides[get_backend_client] = override_get_backend_client
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        # Store mock_backend on client for access in tests
        c.mock_backend = mock_backend
        yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_keys_requires_tg_id(client):
    # User without tg_id => 403
    client.cookies.set("access_token", make_auth_token(tg_id=None))
    resp = await client.get("/api/v1/keys/")
    assert resp.status_code == 403
    assert "Telegram account required" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_list_keys_with_tg_id(client):
    # User with tg_id => calls backend
    client.mock_backend.list_keys = AsyncMock(return_value=[
        {
            "client_id": "test-id",
            "email": "test@example.com",
            "key": "http://sub.example.com/sub/test",
            "expiry_time": 1234567890,
            "tariff_id": 1,
            "name_tariff": "Basic",
            "amount": 0,
            "period": 30,
            "used_traffic": 0,
            "total_gb": 10,
        }
    ])
    client.cookies.set("access_token", make_auth_token(tg_id=123))
    resp = await client.get("/api/v1/keys/")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["email"] == "test@example.com"
    client.mock_backend.list_keys.assert_called_once()


@pytest.mark.asyncio
async def test_list_keys_unauthorized(client):
    # No auth token => 401
    resp = await client.get("/api/v1/keys/")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_delete_key_requires_tg_id(client):
    # User without tg_id => 403
    client.cookies.set("access_token", make_auth_token(tg_id=None))
    resp = await client.delete("/api/v1/keys/test@example.com")
    assert resp.status_code == 403
    assert "Telegram account required" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_delete_key_with_tg_id(client):
    # User with tg_id => calls backend.delete_key
    client.mock_backend.delete_key = AsyncMock(return_value=None)
    client.cookies.set("access_token", make_auth_token(tg_id=123))
    resp = await client.delete("/api/v1/keys/test@example.com")
    assert resp.status_code == 204
    client.mock_backend.delete_key.assert_called_once_with("test@example.com")


@pytest.mark.asyncio
async def test_get_key_with_tg_id(client):
    # User with tg_id => calls backend.get_key
    client.mock_backend.get_key = AsyncMock(return_value={
        "client_id": "test-id",
        "email": "test@example.com",
        "key": "http://sub.example.com/sub/test",
        "expiry_time": 1234567890,
        "tariff_id": 1,
        "name_tariff": "Basic",
        "amount": 0,
        "period": 30,
        "used_traffic": 0,
        "total_gb": 10,
    })
    client.cookies.set("access_token", make_auth_token(tg_id=123))
    resp = await client.get("/api/v1/keys/test@example.com")
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "test@example.com"
    client.mock_backend.get_key.assert_called_once_with("test@example.com")


@pytest.mark.asyncio
async def test_create_key_with_tg_id(client):
    # User with tg_id => calls backend.create_key
    client.mock_backend.create_key = AsyncMock(return_value={
        "client_id": "new-id",
        "email": "new@example.com",
        "key": "http://sub.example.com/sub/new",
        "expiry_time": 1234567890,
        "tariff_id": 1,
        "name_tariff": "Basic",
        "amount": 0,
        "period": 30,
        "used_traffic": 0,
        "total_gb": 10,
    })
    client.cookies.set("access_token", make_auth_token(tg_id=123))
    resp = await client.post("/api/v1/keys/", json={"tariff_id": 1})
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "new@example.com"
    client.mock_backend.create_key.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_renew_key_with_tg_id(client):
    # User with tg_id => calls backend.renew_key
    client.mock_backend.renew_key = AsyncMock(return_value={
        "client_id": "test-id",
        "email": "test@example.com",
        "key": "http://sub.example.com/sub/test",
        "expiry_time": 1234567890,
        "tariff_id": 1,
        "name_tariff": "Basic",
        "amount": 0,
        "period": 30,
        "used_traffic": 0,
        "total_gb": 10,
    })
    client.cookies.set("access_token", make_auth_token(tg_id=123))
    resp = await client.post("/api/v1/keys/test@example.com/renew", json={"tariff_id": 1})
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "test@example.com"
    client.mock_backend.renew_key.assert_called_once_with("test@example.com", 123, 1, months=1)


@pytest.mark.asyncio
async def test_create_trial_key_success(client):
    client.mock_backend.create_trial_key = AsyncMock(return_value={
        "client_id": "trial-id",
        "email": "trial@123.vpn",
        "key": "https://sub.example.com/trial",
        "expiry_time": 9999999999000,
        "tariff_id": 10,
        "name_tariff": "Пробный",
        "amount": 0,
        "period": 30,
        "used_traffic": 0,
        "total_gb": 0,
    })
    client.cookies.set("access_token", make_auth_token(tg_id=123))

    resp = await client.post("/api/v1/keys/trial")

    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "trial@123.vpn"
    client.mock_backend.create_trial_key.assert_called_once()


@pytest.mark.asyncio
async def test_create_trial_key_requires_tg_id(client):
    token = create_access_token({"sub": "1", "tg_id": None, "is_admin": False})
    client.cookies.set("access_token", token)

    resp = await client.post("/api/v1/keys/trial")

    assert resp.status_code == 403
