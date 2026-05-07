"""Integration tests for auth flow with backend simulation"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from httpx import HTTPStatusError, Request, Response
from app.schemas.auth import UserResponse
from datetime import datetime, timezone


@pytest.mark.asyncio
async def test_new_user_complete_flow(client):
    """Full flow: new user from Telegram → check backend → create → JWT"""
    from app.core.dependencies import get_backend_client

    # Mock WebBackendClient
    mock_backend = AsyncMock()

    # Step 1: GET /users/{tg_id} returns 404
    mock_response_404 = Response(404)
    mock_backend.get_user.side_effect = HTTPStatusError(
        "404 Not Found",
        request=Request("GET", "http://test/users/999"),
        response=mock_response_404
    )

    # Step 2: POST /users creates user
    created_user = UserResponse(
        tg_id=999,
        is_admin=False,
        balance=0.0,
        server_id=1,
        created_at=datetime.now(timezone.utc),
        username="newuser999"
    )
    mock_backend.create_user.return_value = created_user

    # Inject mock
    client.app.dependency_overrides[get_backend_client] = lambda: mock_backend

    # Act: Send login request
    response = client.post(
        "/api/v1/auth/telegram-callback",
        json={
            "telegram_data": {"id": 999, "first_name": "NewUser", "hash": "valid_hash"},
            "captcha_token": "token",
            "captcha_timestamp": 1234567890,
            "captcha_answer": 2
        }
    )

    # Assert: Success
    assert response.status_code == 200, f"Got {response.status_code}: {response.json()}"
    assert "access_token" in response.cookies

    # Verify backend calls
    mock_backend.get_user.assert_called_once_with(999)
    mock_backend.create_user.assert_called_once_with(999)

    # Cleanup
    client.app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_existing_user_complete_flow(client):
    """Full flow: existing user from Telegram → check backend → use existing → JWT"""
    from app.core.dependencies import get_backend_client

    mock_backend = AsyncMock()

    # User exists in backend
    existing_user = UserResponse(
        tg_id=777,
        is_admin=True,
        balance=50.0,
        server_id=2,
        created_at=datetime.now(timezone.utc),
        username="existinguser"
    )
    mock_backend.get_user.return_value = existing_user

    # Inject mock
    client.app.dependency_overrides[get_backend_client] = lambda: mock_backend

    # Act: Send login request
    response = client.post(
        "/api/v1/auth/telegram-callback",
        json={
            "telegram_data": {"id": 777, "first_name": "Existing", "hash": "valid_hash"},
            "captcha_token": "token",
            "captcha_timestamp": 1234567890,
            "captcha_answer": 2
        }
    )

    # Assert: Success
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["is_admin"] is True

    # Verify backend calls
    mock_backend.get_user.assert_called_once_with(777)
    mock_backend.create_user.assert_not_called()

    # Cleanup
    client.app.dependency_overrides.clear()
