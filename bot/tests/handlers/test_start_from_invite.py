"""Tests for start command handler with invite token."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.types import Message, User as TelegramUser
from aiogram.fsm.context import FSMContext

from handlers.start_from_invite import handle_start_with_invite
from services.auth_service import BotAuthService
from api.backend_client import BackendAPIClient


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
    """Create a mock Telegram message."""
    msg = MagicMock(spec=Message)
    msg.from_user = mock_telegram_user
    msg.text = "/start test_invite_token"
    msg.answer = AsyncMock()
    return msg


@pytest.fixture
def mock_state():
    """Create a mock FSMContext."""
    state = MagicMock(spec=FSMContext)
    state.update_data = AsyncMock()
    return state


@pytest.fixture
def mock_backend_client():
    """Create a mock BackendAPIClient."""
    client = MagicMock(spec=BackendAPIClient)
    client.get_user = AsyncMock()
    client.register_from_invite = AsyncMock()
    return client


@pytest.mark.asyncio
async def test_start_without_token(mock_message, mock_state, mock_backend_client):
    """Test /start without token returns error."""
    mock_message.text = "/start"

    await handle_start_with_invite(
        mock_message, mock_state, mock_backend_client, "test_invite_token"
    )

    mock_message.answer.assert_called_once()
    call_args = mock_message.answer.call_args[0][0]
    assert "Invalid start command" in call_args


@pytest.mark.asyncio
async def test_start_with_invalid_token(mock_message, mock_state, mock_backend_client):
    """Test /start with invalid token returns error."""
    mock_message.text = "/start wrong_token"

    await handle_start_with_invite(
        mock_message, mock_state, mock_backend_client, "test_invite_token"
    )

    mock_message.answer.assert_called_once()
    call_args = mock_message.answer.call_args[0][0]
    assert "Invalid invite token" in call_args


@pytest.mark.asyncio
async def test_start_with_valid_token(
    mock_message, mock_state, mock_backend_client, mock_telegram_user
):
    """Test /start with valid token generates login code."""
    mock_message.text = "/start test_invite_token"

    # Mock the register_from_invite response
    mock_response = MagicMock()
    mock_response.login_code = "ABC12345"
    mock_backend_client.register_from_invite = AsyncMock(return_value=mock_response)

    await handle_start_with_invite(
        mock_message, mock_state, mock_backend_client, "test_invite_token"
    )

    # Verify answer was called with success message
    mock_message.answer.assert_called_once()
    call_args = mock_message.answer.call_args[0][0]
    assert "ABC12345" in call_args
    assert "Welcome" in call_args

    # Verify state was updated
    mock_state.update_data.assert_called_once()
    update_data_call = mock_state.update_data.call_args[1]
    assert update_data_call["tg_id"] == mock_telegram_user.id
    assert update_data_call["login_code"] == "ABC12345"
    assert update_data_call["invite_processed"] is True


@pytest.mark.asyncio
async def test_start_without_from_user(mock_message, mock_state, mock_backend_client):
    """Test /start without from_user field."""
    mock_message.from_user = None

    await handle_start_with_invite(
        mock_message, mock_state, mock_backend_client, "test_invite_token"
    )

    # Should not attempt to send any message
    mock_message.answer.assert_not_called()


@pytest.mark.asyncio
async def test_start_registration_failure(mock_message, mock_state, mock_backend_client):
    """Test /start when registration fails."""
    mock_message.text = "/start test_invite_token"

    # Mock registration failure
    mock_backend_client.register_from_invite = AsyncMock(side_effect=Exception("API error"))

    await handle_start_with_invite(
        mock_message, mock_state, mock_backend_client, "test_invite_token"
    )

    # Verify failure message was sent
    mock_message.answer.assert_called_once()
    call_args = mock_message.answer.call_args[0][0]
    assert "Registration failed" in call_args or "failed" in call_args.lower()


@pytest.mark.asyncio
async def test_start_with_minimal_user_data(mock_state, mock_backend_client):
    """Test /start with minimal user data (no username, last_name)."""
    # Create user with minimal data
    minimal_user = TelegramUser(
        id=99999999,
        is_bot=False,
        first_name="Test",
        language_code="en",
    )

    msg = MagicMock(spec=Message)
    msg.from_user = minimal_user
    msg.text = "/start test_invite_token"
    msg.answer = AsyncMock()

    # Mock the response
    mock_response = MagicMock()
    mock_response.login_code = "XYZ98765"
    mock_backend_client.register_from_invite = AsyncMock(return_value=mock_response)

    await handle_start_with_invite(
        msg, mock_state, mock_backend_client, "test_invite_token"
    )

    # Verify it handles minimal data gracefully
    msg.answer.assert_called_once()
    call_args = msg.answer.call_args[0][0]
    assert "XYZ98765" in call_args
