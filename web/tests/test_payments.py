"""Тесты эндпоинтов платежей (backend API).

Проверяют требование авторизации для создания платежа и webhook-обработку.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.dependencies import get_backend_client
from app.api.backend_client import WebBackendClient


async def mock_get_backend_client(request=None, current_user=None):
    """Mock backend client — returns MagicMock with async methods."""
    client = MagicMock(spec=WebBackendClient)
    client.get_payment_history = AsyncMock(return_value=[])
    client.create_payment = AsyncMock(return_value={
        "payment_id": "test_payment_id",
        "confirmation_url": "https://payment.example.com",
        "amount": 100.0,
    })
    client.create_renewal_payment = AsyncMock(return_value={
        "payment_id": "test_renewal_id",
        "confirmation_url": "https://payment.example.com",
        "amount": 100.0,
    })
    client.get_payment_status = AsyncMock(return_value={
        "payment_id": "test_payment_id",
        "status": "pending",
        "processed": False,
    })
    return client


@pytest.fixture(autouse=True)
def override_deps():
    app.dependency_overrides[get_backend_client] = mock_get_backend_client
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
async def test_webhook_ok(client):
    # Webhook accepts any payload and returns 200
    resp = await client.post("/api/v1/payments/webhook", json={"test": "data"})
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
