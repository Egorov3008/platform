"""Тесты эндпоинтов платежей (YooKassa).

Проверяют требование авторизации для создания платежа и обработку
некорректного webhook-запроса.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.dependencies import get_conn


async def mock_get_conn():
    """Mock DB connection — yields a MagicMock so no real pool needed."""
    conn = MagicMock()
    conn.fetchrow = AsyncMock(return_value=None)
    conn.execute = AsyncMock(return_value=None)
    yield conn


@pytest.fixture(autouse=True)
def override_deps():
    app.dependency_overrides[get_conn] = mock_get_conn
    yield
    app.dependency_overrides.clear()


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_create_payment_unauthorized(client):
    # No cookie → 401
    resp = await client.post("/api/v1/payments/create", json={"tariff_id": 1})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_webhook_invalid_json(client):
    resp = await client.post(
        "/api/v1/payments/webhook",
        content=b"not-json",
        headers={"content-type": "application/octet-stream"},
    )
    # Either 400 (invalid JSON) or 422 (unprocessable) is acceptable
    assert resp.status_code in (400, 422)
