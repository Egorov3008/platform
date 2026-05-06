"""Handler for /start command with invite token parameter."""
import logging

from aiogram import Router
from aiogram.filters import BaseFilter, Command
from aiogram.types import Message

from api.backend_client import BackendAPIClient
from config import INVITE_TOKEN
from services.auth_service import BotAuthService

logger = logging.getLogger(__name__)

router = Router()


class InviteTokenFilter(BaseFilter):
    def __init__(self, token: str):
        self.token = token

    async def __call__(self, message: Message) -> bool:
        if not message.text:
            return False
        parts = message.text.split()
        return len(parts) > 1 and parts[1] == self.token


@router.message(Command("start"), InviteTokenFilter(INVITE_TOKEN))
async def handle_start_with_invite(
    message: Message,
    container,
) -> None:
    """Handle /start <INVITE_TOKEN> — generate web login code."""
    if not message.from_user:
        return

    tg_id = message.from_user.id
    parts = (message.text or "").split()
    received_token = parts[1] if len(parts) > 1 else None

    backend_client = container.resolve(BackendAPIClient)
    auth_service = BotAuthService(backend_client, INVITE_TOKEN)

    login_code = await auth_service.get_or_register_user(
        tg_id=tg_id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        language_code=message.from_user.language_code or "en",
        invite_token=received_token,
    )

    if not login_code:
        await message.answer(
            "❌ Не удалось сгенерировать код. Попробуйте позже или обратитесь в поддержку."
        )
        logger.error(f"Failed to generate login code: tg_id={tg_id}")
        return

    await message.answer(
        f"🔑 Ваш код для входа в веб-кабинет:\n\n"
        f"<code>{login_code}</code>\n\n"
        f"Введите этот код на сайте для авторизации.",
        parse_mode="HTML",
    )
    logger.info(f"Login code sent via invite: tg_id={tg_id}")
