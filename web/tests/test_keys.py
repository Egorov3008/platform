"""Тесты эндпоинтов управления ключами.

Проверяют авторизацию, обработку пустого списка ключей для пользователей
без tg_id и корректность кодов ошибок при удалении.
"""

import pytest
from unittest.mock import AsyncMock
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.dependencies import get_conn, get_current_user
from app.core.security import create_access_token


def make_auth_token(tg_id=None):
    return create_access_token({"sub": "1", "tg_id": tg_id, "is_admin": False})


@pytest.fixture
async def client():
    mock_conn = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=[])
    mock_conn.fetchrow = AsyncMock(return_value=None)

    async def override_get_conn():
        yield mock_conn

    app.dependency_overrides[get_conn] = override_get_conn
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_keys_empty(client):
    # User without tg_id gets empty list
    client.cookies.set("access_token", make_auth_token(tg_id=None))
    resp = await client.get("/api/v1/keys/")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_keys_unauthorized(client):
    resp = await client.get("/api/v1/keys/")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_delete_key_not_found(client):
    # User without tg_id => 403 (requires telegram account)
    client.cookies.set("access_token", make_auth_token(tg_id=None))
    resp = await client.delete("/api/v1/keys/nonexistent-uuid")
    assert resp.status_code == 403
