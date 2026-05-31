"""Клавиатура для изменения тарифа ключа."""

from typing import Any

from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, StartMode
from aiogram_dialog.widgets.kbd import (
    Column,
    Button,
    Cancel,
    Select,
    SwitchTo,
)
from aiogram_dialog.widgets.text import Const, Format

from api.backend_client import BackendAPIClient
from dialogs.windows.base import KeyboardBuilder
from logger import logger
from states import AdminKeyChangeTariffSG, AdminManager


class AdminKeyChangeTariffKeyboard(KeyboardBuilder):
    """Клавиатура выбора тарифа (pick_tariff state)."""

    def build(self):
        return Column(
            Select(
                Format("{item[1].name_tariff} ({item[1].amount}₽)"),
                id="s_tariff",
                items="tariff_list",
                item_id_getter=lambda x: str(x[0]),
                on_click=self._on_tariff_selected,
            ),
            Cancel(Const("🔙 Назад")),
        )

    @staticmethod
    async def _on_tariff_selected(
        callback: CallbackQuery,
        widget: Any,
        manager: DialogManager,
        item_id: str,
    ):
        """Обработчик выбора тарифа."""
        try:
            manager.dialog_data["selected_tariff_id"] = int(item_id)
            await manager.switch_to(AdminKeyChangeTariffSG.confirm)
            await callback.answer("✅ Тариф выбран", show_alert=False)
        except Exception as e:
            logger.error("Ошибка при выборе тарифа", error=str(e), exc_info=True)
            await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


class AdminKeyChangeTariffConfirmKeyboard(KeyboardBuilder):
    """Клавиатура подтверждения изменения тарифа (confirm state)."""

    def build(self):
        return Column(
            Button(
                Const("✅ Подтвердить"),
                id="confirm_tariff",
                on_click=self._on_confirm,
            ),
            SwitchTo(
                Const("🔄 Выбрать другой тариф"),
                id="back_tariff",
                state=AdminKeyChangeTariffSG.pick_tariff,
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
        """Подтвердить изменение тарифа через backend API."""
        email = manager.start_data.get("email")
        selected_tariff_id = manager.dialog_data.get("selected_tariff_id")

        if not email or not selected_tariff_id:
            await callback.answer("❌ Некорректные данные", show_alert=True)
            return

        try:
            container = manager.middleware_data.get("container")
            if not container:
                await callback.answer("❌ Сервис недоступен", show_alert=True)
                return

            backend = container.resolve(BackendAPIClient)
            success = await backend.admin_change_key_tariff(email, selected_tariff_id)
            if not success:
                await callback.answer("❌ Не удалось изменить тариф", show_alert=True)
                return

            logger.info("Тариф ключа обновлён через backend", email=email, new_tariff_id=selected_tariff_id)
            await callback.answer("✅ Тариф изменён", show_alert=True)

            # Вернуться в список ключей
            await manager.start(AdminManager.key_list, mode=StartMode.RESET_STACK)

        except Exception as e:
            logger.error(
                "Ошибка при обновлении тарифа ключа",
                email=email,
                error=str(e),
                exc_info=True,
            )
            await callback.answer(
                f"❌ Ошибка при обновлении: {str(e)}", show_alert=True
            )
