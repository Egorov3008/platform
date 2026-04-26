"""Тесты административных эндпоинтов.

Проверяют, что все admin-маршруты требуют авторизацию с правами
администратора (возвращают 403 без валидного токена).
"""

import pytest
from unittest.mock import AsyncMock
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.dependencies import get_conn


@pytest.fixture
async def client():
    mock_conn = AsyncMock()

    async def override_get_conn():
        yield mock_conn

    app.dependency_overrides[get_conn] = override_get_conn
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_stats_requires_admin(client):
    resp = await client.get("/api/v1/admin/stats")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_users_requires_admin(client):
    resp = await client.get("/api/v1/admin/users")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_keys_requires_admin(client):
    resp = await client.get("/api/v1/admin/keys")
    assert resp.status_code == 401
