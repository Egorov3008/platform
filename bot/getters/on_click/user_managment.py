from typing import Optional

from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import Button

from api.backend_client import BackendAPIClient
from bot_project import bot
from config import ADMIN_ID
from logger import logger
from states.admin import AdminSearchManagementSG
from states.registrate import Register


async def on_click_search_tg_id(
    message: Message, widget: TextInput, dialog_manager: DialogManager, text: str
):
    """Кликер для поиска пользователя по tg_id через Backend API."""
    tg_id = int(text)
    logger.debug("Поиск пользователя по tg_id", tg_id=tg_id)

    container = dialog_manager.middleware_data.get("container")
    backend = container.resolve(BackendAPIClient) if container else None

    if not backend:
        await message.answer("❌ Ошибка: не удалось получить доступ к backend")
        return

    user = await backend.get_user(tg_id)
    if not user:
        logger.warning("Пользователь не найден в backend при поиске", tg_id=tg_id)
        await message.answer(f"❌ Пользователь с ID {tg_id} не найден в системе")
        dialog_manager.dialog_data.clear()
        await dialog_manager.switch_to(AdminSearchManagementSG.main)
        return

    dialog_manager.dialog_data["tg_id"] = tg_id
    await dialog_manager.switch_to(AdminSearchManagementSG.profile_user)


async def on_click_search_email(
    message: Message, widget: TextInput, dialog_manager: DialogManager, text: str
):
    """Кликер для поиска пользователя по email через Backend API."""
    email = str(text).strip().lower()
    logger.debug("Поиск пользователя по email", email=email)

    container = dialog_manager.middleware_data.get("container")
    backend = container.resolve(BackendAPIClient) if container else None

    if not backend:
        await message.answer("❌ Ошибка: не удалось получить доступ к backend")
        return

    key = await backend.get_key(email)
    if not key:
        logger.warning("Ключ не найден в backend при поиске", email=email)
        await message.answer(f"❌ Ключ с email {email} не найден в системе")
        dialog_manager.dialog_data.clear()
        await dialog_manager.switch_to(AdminSearchManagementSG.main)
        return

    dialog_manager.dialog_data["email"] = email
    dialog_manager.dialog_data["tg_id"] = key.tg_id
    await dialog_manager.switch_to(AdminSearchManagementSG.profile_user)


async def on_click_search_username(
    message: Message, widget: TextInput, dialog_manager: DialogManager, text: str
):
    """Кликер для отображения пригласившего пользователя."""
    username = str(text)
    dialog_manager.dialog_data["username"] = username
    await dialog_manager.switch_to(Register.sending_registration)


async def process_submit_request(
    callback_query: CallbackQuery, button: Button, dialog_manager: DialogManager
) -> None:
    """Обработка запроса на регистрацию."""
    try:
        await callback_query.answer(
            "Ваша заявка отправлена администратору!\nОжидайте ответа", show_alert=True
        )

        username = dialog_manager.dialog_data["username"]
        user = dialog_manager.event.from_user
        keyboard = InlineKeyboardBuilder()
        keyboard.row(
            InlineKeyboardButton(
                text="Добавить пользователя", callback_data=f"addUser_{user.id}"
            )
        )

        if not await process_user_registration(dialog_manager):
            for admin_id in ADMIN_ID:
                await bot.send_message(
                    chat_id=admin_id,
                    text=(
                        f"Пользователь оставил заявку на регистрацию:\n\n"
                        f"🆔 ID: <code>{user.id}</code>\n"
                        f"👤 Имя: {user.first_name} {user.last_name}\n"
                        f"🔗 Username: @{user.username}\n"
                        f"Приглашён: {username}"
                    ),
                    reply_markup=keyboard.as_markup(),
                )

    except Exception as e:
        logger.error(
            "Ошибка при отправке сообщения",
            user_id=user.id if "user" in locals() else None,
            error_type=type(e).__name__,
            error_message=str(e),
            exc_info=True,
        )
        return


async def process_user_registration(dialog_manager: DialogManager) -> bool:
    """Проверка отправленной заявки на регистрацию через Backend API."""
    user_id = dialog_manager.event.from_user.id
    container = dialog_manager.middleware_data.get("container")
    if not container:
        return False

    backend = container.resolve(BackendAPIClient)
    user = await backend.get_user(user_id)
    return user is not None
