"""
Обработчики кнопок для работы с ключами в админ-панели с использованием сегментации.
"""

from typing import Optional

from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import Button

from api.backend_client import BackendAPIClient
from models.keys.key import Key
from services.core.keys.segmentation import KeySegmentationService
from services.core.keys.admin_report import KeyAdminReport
from logger import logger
from states import AdminMassRenewal


class AdminKeysHandler:
    """Обработчик для работы с ключами в админ-панели."""

    def __init__(self):
        self.report = KeyAdminReport()

    async def _fetch_keys(self, dialog_manager: DialogManager) -> list[Key]:
        """Fetch all keys from backend API and convert to Key models."""
        container = dialog_manager.middleware_data.get("container")
        backend = container.resolve(BackendAPIClient) if container else None
        if not backend:
            return []
        raw_keys = await backend.admin_list_keys()
        return [Key.from_backend(k) for k in raw_keys]

    async def on_click_24h_keys(
        self, callback: CallbackQuery, button: Button, dialog_manager: DialogManager
    ):
        """Показать ключи, истекающие в 24 часа (включая ACTIVE)."""
        try:
            all_keys = dialog_manager.dialog_data.get("all_keys")
            if not all_keys:
                all_keys = await self._fetch_keys(dialog_manager)

            segmentation = KeySegmentationService()
            expiring_24h = await segmentation.get_expiring_24h(all_keys)

            dialog_manager.dialog_data["current_segment"] = "expiring_24h"
            dialog_manager.dialog_data["filtered_keys"] = expiring_24h

            if len(expiring_24h) == 0:
                await callback.answer(
                    "⏰ Ключей, истекающих в 24 часа, не найдено", show_alert=True
                )
            else:
                await callback.answer(
                    f"⏰ Найдено ключей: {len(expiring_24h)}. Выберите ключ из списка ниже.",
                    show_alert=True,
                )
                from states import AdminManager
                await dialog_manager.switch_to(AdminManager.key_list)
            logger.info("Показаны ключи, истекающие в 24ч", count=len(expiring_24h))

        except Exception as e:
            logger.error(
                "Ошибка при отображении ключей на 24ч", error=str(e), exc_info=True
            )
            await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)

    async def on_click_expired_keys(
        self, callback: CallbackQuery, button: Button, dialog_manager: DialogManager
    ):
        """Показать истёкшие ключи."""
        try:
            all_keys = dialog_manager.dialog_data.get("all_keys")
            if not all_keys:
                all_keys = await self._fetch_keys(dialog_manager)

            segmentation = KeySegmentationService()
            expired = await segmentation.get_expired(all_keys)

            dialog_manager.dialog_data["current_segment"] = "expired"
            dialog_manager.dialog_data["filtered_keys"] = expired

            if len(expired) == 0:
                await callback.answer("🔴 Истёкших ключей не найдено", show_alert=True)
            else:
                await callback.answer(
                    f"🔴 Найдено ключей: {len(expired)}. Выберите ключ из списка ниже.",
                    show_alert=True,
                )
                from states import AdminManager
                await dialog_manager.switch_to(AdminManager.key_list)
            logger.info("Показаны истёкшие ключи", count=len(expired))

        except Exception as e:
            logger.error(
                "Ошибка при отображении истёкших ключей", error=str(e), exc_info=True
            )
            await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)

    async def on_click_all_keys(
        self, callback: CallbackQuery, button: Button, dialog_manager: DialogManager
    ):
        """Показать все ключи."""
        try:
            all_keys = dialog_manager.dialog_data.get("all_keys")
            if not all_keys:
                all_keys = await self._fetch_keys(dialog_manager)

            dialog_manager.dialog_data["current_segment"] = "all"
            dialog_manager.dialog_data["filtered_keys"] = all_keys

            if len(all_keys) == 0:
                await callback.answer("🔹 Ключи не найдены", show_alert=True)
            else:
                await callback.answer(
                    f"🔹 Найдено ключей: {len(all_keys)}. Выберите ключ из списка ниже.",
                    show_alert=True,
                )
                from states import AdminManager
                await dialog_manager.switch_to(AdminManager.key_list)
            logger.info("Показаны все ключи", count=len(all_keys))

        except Exception as e:
            logger.error(
                "Ошибка при отображении всех ключей", error=str(e), exc_info=True
            )
            await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)

    async def on_key_selected(
        self, callback: CallbackQuery, widget, manager: DialogManager, item_id: str
    ):
        """Обработчик выбора ключа из списка."""
        try:
            filtered_keys = manager.dialog_data.get("filtered_keys", [])

            if not filtered_keys:
                await callback.answer("❌ Ключи не загружены", show_alert=True)
                return

            selected_key = None
            for key in filtered_keys:
                if key.email == item_id:
                    selected_key = key
                    break

            if not selected_key:
                await callback.answer("❌ Ключ не найден", show_alert=True)
                return

            manager.dialog_data["selected_key"] = selected_key
            manager.dialog_data["selected_key_email"] = selected_key.email

            message = (
                f"✅ Выбран ключ:\n"
                f"<code>{selected_key.email}</code>\n\n"
                f"ID пользователя: <code>{selected_key.tg_id}</code>"
            )

            await callback.answer(message, show_alert=True)
            logger.debug("Ключ выбран для администрирования", email=selected_key.email)

        except Exception as e:
            logger.error("Ошибка при выборе ключа", error=str(e), exc_info=True)
            await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


# Создаём экземпляр обработчика
_handler = AdminKeysHandler()

# Экспортируем методы для использования в клавиатурах
on_click_24h_keys = _handler.on_click_24h_keys
on_click_expired_keys = _handler.on_click_expired_keys
on_click_all_keys = _handler.on_click_all_keys
on_key_selected = _handler.on_key_selected


async def on_input_renewal_days(
    message: Message,
    widget: TextInput,
    dialog_manager: DialogManager,
    text: str,
):
    """Обработчик ввода количества дней для продления."""
    try:
        days = int(text)
        if days <= 0 or days > 3650:  # Максимум 10 лет
            await message.answer(
                "❌ Количество дней должно быть от 1 до 3650. Введите заново:"
            )
            return

        dialog_manager.dialog_data["renewal_days"] = days
        await dialog_manager.switch_to(AdminMassRenewal.preview)

    except ValueError:
        await message.answer(
            "❌ Введите корректное число дней (например: 30, 60, 90):"
        )
