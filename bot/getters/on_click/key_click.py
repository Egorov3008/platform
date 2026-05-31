from datetime import datetime

from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Select, Calendar

from api.backend_client import BackendAPIClient
from logger import logger
from states.admin import AdminManager
from states.key import KeysInit


async def on_click_view_key(
    callback: CallbackQuery, widget: Select, dialog_manager: DialogManager, item_id: str
):
    """Обрабатывает выбор ключа"""
    email = dialog_manager.dialog_data.get(item_id)
    dialog_manager.dialog_data["email"] = email
    await dialog_manager.switch_to(KeysInit.key)


async def on_click_view_key_admin(
    callback: CallbackQuery, widget: Select, dialog_manager: DialogManager, item_id: str
):
    """Обрабатывает выбор ключа через Backend API."""
    email = str(item_id)
    container = dialog_manager.middleware_data.get("container")
    backend = container.resolve(BackendAPIClient) if container else None
    if not backend:
        logger.error("BackendAPIClient not available in key_click")
        await callback.answer("❌ Ошибка сервиса", show_alert=True)
        return
    key = await backend.get_key(email)
    await dialog_manager.start(AdminManager.key_details, data={"selected_key": key})


async def on_date_selected(
    callback: CallbackQuery,
    widget: Calendar,
    dialog_manager: DialogManager,
    selected_date: datetime,
):
    """Обработчик выбора даты в календаре (диалог больше не доступен)"""
    dialog_manager.dialog_data["selected_date"] = selected_date
    logger.debug("Выбрана дата:", data=selected_date.strftime("%d.%m.%Y %H:%M:%S"))
    logger.warning("AdminKeyManagementSG диалог больше не доступен - функция отключена")
