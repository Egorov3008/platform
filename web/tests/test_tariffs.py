"""Тесты публичных эндпоинтов тарифов.

Проверяют доступность списка тарифов без авторизации и корректный
ответ при запросе несуществующего тарифа. Тестируют фильтрацию по админ статусу.
"""

import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.dependencies import get_backend_client_no_auth


@pytest.fixture
async def client():
    # Mock the backend client methods directly
    from app.api.backend_client import WebBackendClient

    mock_backend = AsyncMock()
    mock_backend.list_tariffs = AsyncMock(
        return_value=[
            {
                "id": 1,
                "name_tariff": "Tariff 1",
                "amount": 100,
                "limit_ip": 2,
                "period": 30,
                "traffic_limit": 1000.0
            },
            {
                "id": 2,
                "name_tariff": "Tariff 2",
                "amount": 200,
                "limit_ip": 5,
                "period": 30,
                "traffic_limit": 5000.0
            },
            {
                "id": 3,
                "name_tariff": "Tariff 3",
                "amount": 300,
                "limit_ip": 10,
                "period": 30,
                "traffic_limit": 10000.0
            },
        ]
    )

    async def mock_get_tariff(tariff_id):
        tariffs_map = {
            1: {
                "id": 1,
                "name_tariff": "Tariff 1",
                "amount": 100,
                "limit_ip": 2,
                "period": 30,
                "traffic_limit": 1000.0
            },
            2: {
                "id": 2,
                "name_tariff": "Tariff 2",
                "amount": 200,
                "limit_ip": 5,
                "period": 30,
                "traffic_limit": 5000.0
            },
            3: {
                "id": 3,
                "name_tariff": "Tariff 3",
                "amount": 300,
                "limit_ip": 10,
                "period": 30,
                "traffic_limit": 10000.0
            },
        }
        if tariff_id in tariffs_map:
            return tariffs_map[tariff_id]
        else:
            # Simulate 404 error
            from httpx import HTTPStatusError, Request, Response
            raise HTTPStatusError(
                "404 Not Found",
                request=Request("GET", f"/api/v1/tariffs/{tariff_id}"),
                response=Response(404)
            )

    mock_backend.get_tariff = AsyncMock(side_effect=mock_get_tariff)

    async def override_get_backend_client_no_auth():
        return mock_backend

    app.dependency_overrides[get_backend_client_no_auth] = override_get_backend_client_no_auth
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_tariffs_public(client):
    # For public users without available_rates filter, should see all tariffs
    with patch("app.core.config.settings.available_rates", []):
        resp = await client.get("/api/v1/tariffs/")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
        assert len(resp.json()) == 3


@pytest.mark.asyncio
async def test_get_tariff_by_id_not_found(client):
    resp = await client.get("/api/v1/tariffs/999999")
    assert resp.status_code == 404  # Tariff not found


@pytest.mark.asyncio
async def test_get_tariffs_unauthenticated_with_available_rates(client):
    """Тест: неавторизованный пользователь видит только AVAILABLE_RATES."""
    with patch("app.core.config.settings.available_rates", [1, 2]):
        resp = await client.get("/api/v1/tariffs/")
        assert resp.status_code == 200
        tariffs = resp.json()
        assert isinstance(tariffs, list)
        assert len(tariffs) == 2
        assert all(t["id"] in [1, 2] for t in tariffs)


@pytest.mark.asyncio
async def test_get_tariffs_admin_sees_all(client):
    """Тест: администратор видит все тарифы при AVAILABLE_RATES."""
    from app.core.security import create_access_token

    with patch("app.core.config.settings.available_rates", [1, 2]):
        token = create_access_token({"sub": "123", "tg_id": 123, "is_admin": True})
        resp = await client.get("/api/v1/tariffs/", cookies={"access_token": token})
        assert resp.status_code == 200
        tariffs = resp.json()
        assert isinstance(tariffs, list)
        assert len(tariffs) == 3  # Admin sees all tariffs
