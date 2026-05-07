"""Тесты для функции login_via_telegram (Task 5)."""

import pytest
from unittest.mock import AsyncMock, patch

from app.services.auth import login_via_telegram


@pytest.mark.asyncio
async def test_login_via_telegram_new_user():
    """Если web_users не найден по tg_id, создаётся новая запись с email tg_<id>@bot.local."""
    conn = AsyncMock()
    new_user = {"id": 101, "tg_id": 555, "email": "tg_555@bot.local"}

    with (
        patch("app.services.auth.web_users_repo.get_by_tg_id", return_value=None),
        patch("app.services.auth.web_users_repo.create", return_value=new_user) as mock_create,
    ):
        access_token, refresh_token = await login_via_telegram(conn, tg_id=555, is_admin=False)

    mock_create.assert_called_once()
    call_kwargs = mock_create.call_args[1]
    assert call_kwargs["email"] == "tg_555@bot.local"
    assert call_kwargs["tg_id"] == 555
    assert call_kwargs["password_hash"]  # должен быть рандомный hash
    assert access_token
    assert refresh_token


@pytest.mark.asyncio
async def test_login_via_telegram_existing_user():
    """Если web_users уже существует, токены выпускаются без вызова create."""
    conn = AsyncMock()
    existing_user = {"id": 77, "tg_id": 999, "email": "tg_999@bot.local"}

    with (
        patch("app.services.auth.web_users_repo.get_by_tg_id", return_value=existing_user),
        patch("app.services.auth.web_users_repo.create") as mock_create,
    ):
        access_token, refresh_token = await login_via_telegram(conn, tg_id=999, is_admin=True)

    mock_create.assert_not_called()
    assert access_token
    assert refresh_token
