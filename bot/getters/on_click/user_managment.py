from typing import Optional

from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import Button

from bot_project import bot
from config import ADMIN_ID
from logger import logger
from services.cache.key_manager import CacheKeyManager
from services.cache.service import CacheService
from states.admin import AdminSearchManagementSG
from states.registrate import Register


async def on_click_search_tg_id(
    message: Message, widget: TextInput, dialog_manager: DialogManager, text: str
):
    """Кликер для поиска пользователя по tg_id с валидацией кеша"""
    tg_id = int(text)
    logger.debug("Поиск пользователя по tg_id", tg_id=tg_id)

    # Проверяем наличие пользователя в кеше ДО переключения диалога
    cache: Optional[CacheService] = dialog_manager.middleware_data.get("cache")
    if not cache:
        await message.answer("❌ Ошибка: не удалось получить доступ к кешу")
        return

    user = await cache.users.get(CacheKeyManager.user(tg_id))
    if not user:
        logger.warning("Пользователь не найден в кеше при поиске", tg_id=tg_id)
        await message.answer(f"❌ Пользователь с ID {tg_id} не найден в системе")
        # Очищаем старые данные перед возвратом в меню
        dialog_manager.dialog_data.clear()
        # Возвращаемся в меню выбора категории поиска
        await dialog_manager.switch_to(AdminSearchManagementSG.main)
        return

    dialog_manager.dialog_data["tg_id"] = tg_id
    await dialog_manager.switch_to(AdminSearchManagementSG.profile_user)


async def on_click_search_email(
    message: Message, widget: TextInput, dialog_manager: DialogManager, text: str
):
    """Кликер для поиска пользователя по email с валидацией кеша"""
    email = str(text).strip().lower()
    logger.debug("Поиск пользователя по email", email=email)

    # Проверяем наличие ключа в кеше ДО переключения диалога
    cache: Optional[CacheService] = dialog_manager.middleware_data.get("cache")
    if not cache:
        await message.answer("❌ Ошибка: не удалось получить доступ к кешу")
        return

    # Ищем ключ по email
    key = await cache.keys.get(CacheKeyManager.key(email))
    if not key:
        logger.warning("Ключ не найден в кеше при поиске", email=email)
        await message.answer(f"❌ Ключ с email {email} не найден в системе")
        # Очищаем старые данные перед возвратом в меню
        dialog_manager.dialog_data.clear()
        # Возвращаемся в меню выбора категории поиска
        await dialog_manager.switch_to(AdminSearchManagementSG.main)
        return

    # Сохраняем email ключа и переходим на профиль пользователя, которому принадлежит этот ключ
    dialog_manager.dialog_data["email"] = email
    dialog_manager.dialog_data["tg_id"] = key.tg_id
    await dialog_manager.switch_to(AdminSearchManagementSG.profile_user)


async def on_click_search_username(
    message: Message, widget: TextInput, dialog_manager: DialogManager, text: str
):
    """Кликер для отображения пригласившего пользователя"""
    username = str(text)
    dialog_manager.dialog_data["username"] = username
    await dialog_manager.switch_to(Register.sending_registration)


async def process_submit_request(
    callback_query: CallbackQuery, button: Button, dialog_manager: DialogManager
) -> None:
    """Обработка запроса на регистрацию"""
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
    """Проверка отправленной заявки на регистрацию"""
    from services.cache.service import CacheService
    from services.cache.key_manager import CacheKeyManager

    user_id = dialog_manager.event.from_user.id
    cache_service = dialog_manager.middleware_data.get("cache")

    if not isinstance(cache_service, CacheService):
        return False

    # Проверяем, зарегистрирован ли пользователь
    cache_key = CacheKeyManager.user(user_id)
    user = await cache_service.users.get(cache_key)
    return user is not None
