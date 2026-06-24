"""Обработчики on-click для генерации ключа администратором."""

from aiogram.types import Message
from aiogram_dialog import DialogManager

from api.backend_client import BackendAPIClient
from states.admin import AdminGenerateKeySG
from logger import logger


async def on_tg_id_entered(
    message: Message, widget, dialog_manager: DialogManager, text: int
):
    """Обработчик ввода tg_id — проверяет существование пользователя через Backend API."""
    tg_id = text
    container = dialog_manager.middleware_data.get("container")
    backend = container.resolve(BackendAPIClient) if container else None

    user_exists = False
    if backend:
        user = await backend.get_user(tg_id)
        user_exists = user is not None

    dialog_manager.dialog_data["tg_id"] = tg_id
    dialog_manager.dialog_data["user_exists"] = user_exists

    logger.info(
        "Админ ввёл tg_id для генерации ключа",
        tg_id=tg_id,
        user_exists=user_exists,
    )

    await dialog_manager.switch_to(AdminGenerateKeySG.choosing_tariff)


async def error_gen_tg_id(
    message: Message, widget, dialog_manager: DialogManager, error
):
    """Обработчик ошибки ввода tg_id."""
    await message.answer("ID должен быть числом!")
