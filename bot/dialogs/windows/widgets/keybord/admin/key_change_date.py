"""Клавиатура для изменения даты истечения ключа."""

import calendar
from datetime import datetime, timezone
from typing import Any

from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, StartMode
from aiogram_dialog.widgets.kbd import (
    Column,
    Button,
    Cancel,
    Calendar,
    CalendarConfig,
    SwitchTo,
)
from aiogram_dialog.widgets.text import Const

from api.backend_client import BackendAPIClient
from dialogs.windows.base import KeyboardBuilder
from logger import logger
from states import AdminKeyChangeDateSG, AdminManager


class AdminKeyChangeDateKeyboard(KeyboardBuilder):
    """Клавиатура выбора даты истечения ключа (pick_date state)."""

    def build(self):
        return Calendar(
                id="calendar",
                on_click=self._on_date_selected,
                config=CalendarConfig(firstweekday=calendar.SUNDAY),
            ),Cancel(Const("🔙 Назад"))

    @staticmethod
    async def _on_date_selected(
        callback: CallbackQuery,
        widget: Calendar,
        manager: DialogManager,
        selected_date: datetime,
    ):
        """Обработчик выбора даты в календаре."""
        try:
            manager.dialog_data["selected_date"] = selected_date
            await manager.switch_to(AdminKeyChangeDateSG.confirm)
        except Exception as e:
            logger.error("Ошибка при выборе даты", error=str(e), exc_info=True)
            if callback:
                await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


class AdminKeyChangeDateConfirmKeyboard(KeyboardBuilder):
    """Клавиатура подтверждения изменения даты (confirm state)."""

    def build(self):
        return Column(
            Button(
                Const("✅ Подтвердить"),
                id="confirm_date",
                on_click=self._on_confirm,
            ),
            SwitchTo(
                Const("📅 Выбрать другую дату"),
                id="back_date",
                state=AdminKeyChangeDateSG.pick_date,
            ),
            Cancel(Const("🔙 Отмена")),
        )

    @staticmethod
    async def _on_confirm(
        callback: CallbackQuery,
        button: Any,
        manager: DialogManager,
        **kwargs,
    ):
        """Подтвердить изменение даты истечения через backend API."""
        email = manager.start_data.get("email")
        selected_date = manager.dialog_data.get("selected_date")

        if not email or not selected_date:
            await callback.answer("❌ Некорректные данные", show_alert=True)
            return

        try:
            container = manager.middleware_data.get("container")
            if not container:
                await callback.answer("❌ Сервис недоступен", show_alert=True)
                return

            backend = container.resolve(BackendAPIClient)

            if not isinstance(selected_date, datetime):
                selected_date = datetime.combine(selected_date, datetime.min.time())
            if selected_date.tzinfo is None:
                selected_date = selected_date.replace(tzinfo=timezone.utc)
            expiry_ms = int(selected_date.timestamp() * 1000)

            success = await backend.admin_change_key_date(email, expiry_ms)
            if not success:
                await callback.answer("❌ Не удалось обновить дату", show_alert=True)
                return

            logger.info(
                "Дата истечения ключа обновлена через backend",
                email=email,
                new_date=selected_date.strftime("%d.%m.%Y"),
            )
            await callback.answer(
                f"✅ Дата истечения обновлена на {selected_date.strftime('%d.%m.%Y')}",
                show_alert=True,
            )

            # Вернуться в список ключей
            await manager.start(AdminManager.key_list, mode=StartMode.RESET_STACK)

        except Exception as e:
            logger.error(
                "Ошибка при обновлении даты ключа",
                email=email,
                error=str(e),
                exc_info=True,
            )
            await callback.answer(
                f"❌ Ошибка при обновлении: {str(e)}", show_alert=True
            )
