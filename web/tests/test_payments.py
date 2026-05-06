"""Тесты эндпоинтов платежей (backend API).

Проверяют требование авторизации для создания платежа и webhook-обработку.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.dependencies import get_backend_client
from app.core.security import create_access_token
from app.api.backend_client import WebBackendClient


def make_auth_token(tg_id=123):
    return create_access_token({"sub": "1", "tg_id": tg_id, "is_admin": False})


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


@pytest.mark.asyncio
async def test_list_payments_with_timezone_naive_datetimes(client):
    """Verify sorting works with timezone-naive datetimes from backend."""
    from datetime import datetime, timezone

    async def mock_backend_with_payments(request=None, current_user=None):
        backend = MagicMock(spec=WebBackendClient)
        # Simulate backend returning naive datetimes (as currently happens)
        backend.get_payment_history = AsyncMock(return_value=[
            {
                "payment_id": "p1",
                "tg_id": 123,
                "amount": 100.0,
                "status": "succeeded",
                "payment_type": "create_key|1",
                "created_at": datetime(2026, 5, 6, 10, 0, 0),  # Naive datetime
            },
            {
                "payment_id": "p2",
                "tg_id": 123,
                "amount": 200.0,
                "status": "pending",
                "payment_type": "create_key|2",
                "created_at": datetime(2026, 5, 6, 11, 0, 0),  # Naive datetime
            },
            {
                "payment_id": "p3",
                "tg_id": 123,
                "amount": 300.0,
                "status": "failed",
                "payment_type": "create_key|3",
                "created_at": None,  # None will use fallback in sorting
            },
        ])
        return backend

    app.dependency_overrides[get_backend_client] = mock_backend_with_payments

    # Set JWT cookie for authentication
    client.cookies.set("access_token", make_auth_token(tg_id=123))

    resp = await client.get("/api/v1/payments/")
    assert resp.status_code == 200

    payments = resp.json()
    assert len(payments) == 3

    # Verify sorting is by created_at descending (None/fallback values come first)
    # p2 (11:00) > p1 (10:00) > p3 (None)
    assert payments[0]["payment_id"] == "p2"
    assert payments[1]["payment_id"] == "p1"
    assert payments[2]["payment_id"] == "p3"

    app.dependency_overrides.clear()
