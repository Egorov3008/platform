import pytest
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException
from app.services.auth import login_with_code, refresh_tokens_from_cookie
from app.core.security import create_refresh_token


@pytest.mark.asyncio
async def test_login_with_valid_code_existing_user():
    conn = AsyncMock()
    fake_record = {"id": 1, "code": "ABCD1234", "tg_id": 123, "used": True}
    fake_user = {"id": 42, "tg_id": 123, "email": "tg_123@bot.local"}

    with (
        patch("app.services.auth.login_codes_repo.consume", return_value=fake_record),
        patch("app.services.auth.web_users_repo.get_by_tg_id", return_value=fake_user),
    ):
        access_token, refresh_token = await login_with_code(conn, "ABCD1234")

    assert access_token
    assert refresh_token


@pytest.mark.asyncio
async def test_login_with_valid_code_new_user_creates_web_user():
    conn = AsyncMock()
    fake_record = {"id": 1, "code": "ABCD1234", "tg_id": 456, "used": True}
    new_user = {"id": 99, "tg_id": 456, "email": "tg_456@bot.local"}

    with (
        patch("app.services.auth.login_codes_repo.consume", return_value=fake_record),
        patch("app.services.auth.web_users_repo.get_by_tg_id", return_value=None),
        patch("app.services.auth.web_users_repo.create", return_value=new_user) as mock_create,
    ):
        access_token, refresh_token = await login_with_code(conn, "ABCD1234")

    mock_create.assert_called_once()
    call_kwargs = mock_create.call_args[1]
    assert call_kwargs["email"] == "tg_456@bot.local"
    assert access_token


@pytest.mark.asyncio
async def test_login_with_invalid_code_raises_400():
    conn = AsyncMock()

    with patch("app.services.auth.login_codes_repo.consume", return_value=None):
        with pytest.raises(HTTPException) as exc_info:
            await login_with_code(conn, "BADCODE1")

    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_refresh_tokens_from_cookie_valid():
    payload = {"sub": "42", "tg_id": 123, "is_admin": False}
    refresh_token = create_refresh_token(payload)

    access_token, new_refresh = await refresh_tokens_from_cookie(refresh_token)

    assert access_token
    assert new_refresh


@pytest.mark.asyncio
async def test_refresh_tokens_from_cookie_invalid_raises_401():
    with pytest.raises(HTTPException) as exc_info:
        await refresh_tokens_from_cookie("invalid.token.here")

    assert exc_info.value.status_code == 401
