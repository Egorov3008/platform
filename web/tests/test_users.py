"""Tests for GET /api/v1/users/me endpoint."""

import pytest
from unittest.mock import AsyncMock
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.dependencies import get_current_user, get_backend_client
from app.core.security import create_access_token
from app.api.backend_client import WebBackendClient
from app.schemas.users import UserResponse
from datetime import datetime


def make_auth_token(tg_id=123):
    return create_access_token({"sub": "1", "tg_id": tg_id, "is_admin": False})


def make_user_response(tg_id=123, trial=0):
    return UserResponse(
        tg_id=tg_id,
        is_admin=False,
        trial=trial,
        created_at=datetime(2024, 1, 1),
    )


@pytest.fixture
async def client():
    mock_backend = AsyncMock(spec=WebBackendClient)

    async def override_backend(request=None, current_user=None):
        return mock_backend

    app.dependency_overrides[get_backend_client] = override_backend
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        c.mock_backend = mock_backend
        yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_me_returns_user(client):
    client.mock_backend.get_user = AsyncMock(return_value=make_user_response(trial=0))
    client.cookies.set("access_token", make_auth_token(tg_id=123))

    resp = await client.get("/api/v1/users/me")

    assert resp.status_code == 200
    data = resp.json()
    assert data["tg_id"] == 123
    assert data["trial"] == 0


@pytest.mark.asyncio
async def test_get_me_requires_tg_id(client):
    token = create_access_token({"sub": "1", "tg_id": None, "is_admin": False})
    client.cookies.set("access_token", token)

    resp = await client.get("/api/v1/users/me")

    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_get_me_unauthenticated(client):
    resp = await client.get("/api/v1/users/me")
    assert resp.status_code == 401
