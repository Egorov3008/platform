"""Утилита авто-регистрации пользователя.

Логика выделена из CaptchaKeyboard._auto_register, чтобы её можно было
переиспользовать из разных мест (капча, веб-вход и т. п.).
"""

import random

import asyncpg
from aiogram.exceptions import TelegramAPIError
from aiogram.types import Message
from aiogram_dialog import DialogManager, StartMode

from config import ADMIN_ID, LIST_AVAILABLE_CONNECTIONS
from logger import logger
from services.cache.key_manager import CacheKeyManager
from services.cache.service import CacheService
from services.core.user.utils.saver import SeverUser
from states.main import MainMenu


async def auto_register_user(
    message: Message, dialog_manager: DialogManager
) -> None:
    """Авто-регистрация пользователя.

    1. Создаёт пользователя через SeverUser.register_user (server_id=2).
    2. Кеширует его в cache.users.
    3. Выбирает случайный inbound из LIST_AVAILABLE_CONNECTIONS и сохраняет
       его в кеше как temporary_inbound.
    4. Уведомляет админов.
    5. Переходит на MainMenu.welcome (RESET_STACK).

    При любой ошибке логирует и отправляет сообщение пользователю.
    """
    tg_id = message.from_user.id
    try:
        container = dialog_manager.middleware_data.get("container")
        cache: CacheService = dialog_manager.middleware_data.get("cache")
        pool: asyncpg.Pool = container.resolve(asyncpg.Pool)
        saver: SeverUser = container.resolve(SeverUser)

        # Создаём пользователя (server_id=2)
        new_user = await saver.register_user(pool, tg_id=tg_id, server_id=2)

        # Кешируем нового пользователя
        await cache.users.set(CacheKeyManager.user(tg_id), new_user)

        # Выбираем случайный inbound из доступных подключений
        inbound_id = random.choice(LIST_AVAILABLE_CONNECTIONS)
        await cache.users.set(
            CacheKeyManager.temporary_inbound(tg_id), str(inbound_id)
        )

        logger.info(
            "Пользователь авто-зарегистрирован",
            tg_id=tg_id,
            inbound_id=inbound_id,
        )

        # Информационное уведомление админам
        await _notify_admins(message)

        # Переходим в главное меню
        await dialog_manager.start(MainMenu.welcome, mode=StartMode.RESET_STACK)

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
