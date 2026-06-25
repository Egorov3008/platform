"""Утилита авто-регистрации пользователя.

Логика выделена из CaptchaKeyboard._auto_register, чтобы её можно было
переиспользовать из разных мест (капча, веб-вход и т. п.).
"""

from aiogram.exceptions import TelegramAPIError
from aiogram.types import Message
from aiogram_dialog import DialogManager, StartMode

from api.backend_client import BackendAPIClient
from config import ADMIN_ID
from logger import logger
from states.main import MainMenu
from typing import Optional


async def register_user_only(
    message: Message, dialog_manager: DialogManager
) -> Optional[dict]:
    """Регистрирует юзера в backend (server_id=2) и уведомляет админов.

    1. Создаёт пользователя через BackendAPIClient.admin_register_user (server_id=2).
    2. Уведомляет админов.
    НЕ стартует диалог — вызывающий сам решает, куда перейти.

    Возвращает dict нового юзера или None при ошибке.
    """
    tg_id = message.from_user.id
    try:
        container = dialog_manager.middleware_data.get("container")
        backend: BackendAPIClient = container.resolve(BackendAPIClient)

        from_user = message.from_user
        payload = {
            "tg_id": tg_id,
            "username": from_user.username if from_user else None,
            "first_name": from_user.first_name if from_user else None,
            "last_name": from_user.last_name if from_user else None,
            "language_code": from_user.language_code if from_user else None,
            "server_id": 2,
        }

        new_user = await backend.admin_register_user(payload)
        if not new_user or not new_user.get("tg_id"):
            raise RuntimeError("Backend registration failed or returned empty user")

        logger.info(
            "Пользователь авто-зарегистрирован через backend",
            tg_id=tg_id,
        )

        await _notify_admins(message)
        return new_user

    except Exception as e:
        logger.error(
            "Ошибка при авто-регистрации",
            tg_id=tg_id,
            error_type=type(e).__name__,
            error_message=str(e),
            exc_info=True,
        )
        await message.answer(
            "❌ Произошла ошибка при регистрации. Попробуйте позже или напишите /start"
        )
        return None


async def auto_register_user(
    message: Message, dialog_manager: DialogManager
) -> None:
    """Авто-регистрация пользователя через backend API + переход на MainMenu.welcome.

    Эквивалент register_user_only() + dialog_manager.start(MainMenu.welcome).
    """
    new_user = await register_user_only(message, dialog_manager)
    if new_user:
        await dialog_manager.start(MainMenu.welcome, mode=StartMode.RESET_STACK)


async def _notify_admins(message: Message) -> None:
    """Отправляет информационное уведомление админам о новом пользователе."""
    from_user = message.from_user
    tg_id = from_user.id
    name = from_user.full_name or ""
    username = f"@{from_user.username}" if from_user.username else "нет"

    admin_text = (
        "👤 <b>Новая регистрация</b>\n\n"
        f"🆔 ID: <code>{tg_id}</code>\n"
        f"👤 Имя: {name}\n"
        f"🔗 Username: {username}"
    )
    for admin_id in ADMIN_ID:
        try:
            await message.bot.send_message(
                chat_id=admin_id,
                text=admin_text,
                parse_mode="HTML",
            )
        except TelegramAPIError:
            pass
