"""Handler for /start command with invite token parameter."""
import logging
from typing import Optional

from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from config import INVITE_TOKEN
from services.auth_service import BotAuthService
from api.backend_client import BackendAPIClient

logger = logging.getLogger(__name__)

router = Router()


async def handle_start_with_invite(
    message: Message,
    state: FSMContext,
    backend_client: BackendAPIClient,
    invite_token: str = INVITE_TOKEN,
) -> None:
    """Handle /start command with invite token.

    Processes the flow:
    1. Validate invite token from command
    2. Check if user already exists
    3. Generate login code via registration
    4. Send code to user

    Args:
        message: Telegram message with /start command
        state: FSM context for state management
        backend_client: BackendAPIClient for backend communication
        invite_token: The configured invite token for validation
    """
    if not message.from_user:
        logger.warning("Message without from_user received")
        return

    tg_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    language_code = message.from_user.language_code or "en"

    # Initialize auth service
    auth_service = BotAuthService(backend_client, invite_token)

    # Validate invite token from command
    command_text = message.text or ""
    # Extract token from /start token format
    parts = command_text.split()
    received_token = parts[1] if len(parts) > 1 else None

    if not received_token:
        await message.answer(
            "❌ Invalid start command. Please use: /start <invite_token>"
        )
        logger.warning(f"No token provided in start command: tg_id={tg_id}")
        return

    if not auth_service.validate_invite_token(received_token):
        await message.answer(
            "❌ Invalid invite token. Please check your invitation link and try again."
        )
        logger.warning(f"Invalid invite token: tg_id={tg_id}, token={received_token}")
        return

    # Get or register user and generate login code
    login_code = await auth_service.get_or_register_user(
        tg_id=tg_id,
        username=username,
        first_name=first_name,
        last_name=last_name,
        language_code=language_code,
        invite_token=received_token,
    )

    if not login_code:
        await message.answer(
            "❌ Registration failed. Please try again later or contact support."
        )
        logger.error(f"Failed to generate login code: tg_id={tg_id}")
        return

    # Send login code to user
    await message.answer(
        f"✅ Welcome!\n\n"
        f"Your login code: <code>{login_code}</code>\n\n"
        f"Use this code to log in to the web platform.",
        parse_mode="HTML",
    )

    logger.info(f"User start with invite processed: tg_id={tg_id}, code_length={len(login_code)}")

    # Store state for potential next steps
    await state.update_data(
        tg_id=tg_id,
        login_code=login_code,
        invite_processed=True,
    )
