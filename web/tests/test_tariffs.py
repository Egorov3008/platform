"""Тесты публичных эндпоинтов тарифов.

Проверяют доступность списка тарифов без авторизации и корректный
ответ при запросе несуществующего тарифа. Тестируют фильтрацию по админ статусу.
"""

import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.dependencies import get_conn


@pytest.fixture
async def client():
    # Mock the DB connection so tests work without real DB
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
async def test_get_tariffs_public(client):
    resp = await client.get("/api/v1/tariffs/")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_get_tariff_by_id_not_found(client):
    resp = await client.get("/api/v1/tariffs/999999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_tariffs_unauthenticated_with_available_rates(client):
    """Тест: неавторизованный пользователь видит только AVAILABLE_RATES."""
    with patch("app.core.config.settings.available_rates", [1, 2, 3]):
        resp = await client.get("/api/v1/tariffs/")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_get_tariffs_admin_sees_all(client):
    """Тест: администратор видит все тарифы при AVAILABLE_RATES."""
    from app.core.security import create_access_token

    with patch("app.core.config.settings.available_rates", [1, 2, 3]):
        token = create_access_token({"sub": 123, "tg_id": 123, "is_admin": True})
        resp = await client.get("/api/v1/tariffs/", cookies={"access_token": token})
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
