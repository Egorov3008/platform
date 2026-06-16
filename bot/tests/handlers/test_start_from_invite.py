"""Tests for start_from_invite handler — web login code via invite token.

Source: handlers/start_from_invite.py

The handler signature is ``(message, container)`` where ``container`` is a
DI container that resolves ``BackendAPIClient``. The invite token is taken
from the runtime config (default: ``"changeme"`` from config.py).
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from aiogram.types import Message, User as TelegramUser

from handlers.start_from_invite import handle_start_with_invite
from services.auth_service import BotAuthService
from config import INVITE_TOKEN
from api.schemas import RegisterFromInviteResponse


@pytest.fixture
def mock_telegram_user():
    """Create a mock Telegram user."""
    return TelegramUser(
        id=12345678,
        is_bot=False,
        first_name="Test",
        last_name="User",
        username="testuser",
        language_code="en",
    )


@pytest.fixture
def mock_message(mock_telegram_user):
    """Create a mock Telegram message with /start <token>."""
    msg = MagicMock(spec=Message)
    msg.from_user = mock_telegram_user
    msg.text = f"/start {INVITE_TOKEN}"
    msg.answer = AsyncMock()
    return msg


@pytest.fixture
def mock_container(mock_backend_client):
    """Create a mock DI container that resolves BackendAPIClient."""
    container = MagicMock()
    container.resolve = MagicMock(return_value=mock_backend_client)
    return container


def _register_response(login_code: str = "ABC12345") -> RegisterFromInviteResponse:
    """Build a RegisterFromInviteResponse DTO for the backend mock.

    ``login_code`` must match ``^[A-Z0-9]{8}$`` and ``code_expires_at``
    is a required ``datetime`` field.
    """
    from datetime import datetime, timezone
    return RegisterFromInviteResponse(
        login_code=login_code,
        code_expires_at=datetime.now(timezone.utc),
        tg_id=12345678,
        user_id=12345678,
    )


# ---------------------------------------------------------------------------
# handle_start_with_invite — happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_start_with_valid_token(
    mock_message, mock_container, mock_backend_client, mock_telegram_user
):
    """Test /start with valid token returns a login code to the user."""
    mock_backend_client.get_user = AsyncMock(return_value=None)
    mock_backend_client.register_from_invite = AsyncMock(
        return_value=_register_response("ABC12345")
    )

    await handle_start_with_invite(mock_message, mock_container)

    mock_message.answer.assert_called_once()
    call_args = mock_message.answer.call_args[0][0]
    assert "ABC12345" in call_args
    # Must mention the code is for web-cabinet
    assert "код" in call_args.lower() or "code" in call_args.lower()


# ---------------------------------------------------------------------------
# handle_start_with_invite — token validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_start_with_invalid_token(
    mock_message, mock_container, mock_backend_client
):
    """Test /start with invalid token does NOT call backend and shows error."""
    mock_message.text = "/start wrong_token"

    await handle_start_with_invite(mock_message, mock_container)

    # backend must NOT be called
    mock_backend_client.register_from_invite.assert_not_called()
    mock_message.answer.assert_called_once()
    call_args = mock_message.answer.call_args[0][0]
    assert "❌" in call_args or "Не удалось" in call_args


# ---------------------------------------------------------------------------
# handle_start_with_invite — missing from_user
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_start_without_from_user(
    mock_message, mock_container, mock_backend_client
):
    """Test /start without from_user field — handler must early-return silently."""
    mock_message.from_user = None

    await handle_start_with_invite(mock_message, mock_container)

    # Should not attempt to send any message
    mock_message.answer.assert_not_called()
    mock_backend_client.register_from_invite.assert_not_called()


# ---------------------------------------------------------------------------
# handle_start_with_invite — backend failure
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_start_registration_failure(
    mock_message, mock_container, mock_backend_client
):
    """Test /start when backend.register_from_invite raises — user sees error."""
    mock_backend_client.get_user = AsyncMock(return_value=None)
    mock_backend_client.register_from_invite = AsyncMock(
        side_effect=Exception("API error")
    )

    await handle_start_with_invite(mock_message, mock_container)

    mock_message.answer.assert_called_once()
    call_args = mock_message.answer.call_args[0][0]
    # Source: "❌ Не удалось сгенерировать код..."
    assert "❌" in call_args


# ---------------------------------------------------------------------------
# handle_start_with_invite — minimal user data (no username, no last_name)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_start_with_minimal_user_data(
    mock_container, mock_backend_client
):
    """Test /start with minimal user data (no username, no last_name)."""
    minimal_user = TelegramUser(
        id=99999999,
        is_bot=False,
        first_name="Test",
        language_code="en",
    )

    msg = MagicMock(spec=Message)
    msg.from_user = minimal_user
    msg.text = f"/start {INVITE_TOKEN}"
    msg.answer = AsyncMock()

    mock_backend_client.get_user = AsyncMock(return_value=None)
    mock_backend_client.register_from_invite = AsyncMock(
        return_value=_register_response("XYZ98765")
    )

    await handle_start_with_invite(msg, mock_container)

    # Verify it handles minimal data gracefully and surfaces the code
    msg.answer.assert_called_once()
    call_args = msg.answer.call_args[0][0]
    assert "XYZ98765" in call_args


# ---------------------------------------------------------------------------
# handle_start_with_invite — existing user
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_start_existing_user_gets_new_code(
    mock_message, mock_container, mock_backend_client
):
    """When the user already exists, the handler still issues a fresh login code."""
    mock_backend_client.get_user = AsyncMock(return_value={"tg_id": 12345678})
    mock_backend_client.register_from_invite = AsyncMock(
        return_value=_register_response("REFRES42")
    )

    await handle_start_with_invite(mock_message, mock_container)

    mock_backend_client.register_from_invite.assert_awaited_once()
    mock_message.answer.assert_called_once()
    call_args = mock_message.answer.call_args[0][0]
    assert "REFRES42" in call_args
