"""Клавиатура для выбора сегмента и ввода дней массового продления."""

from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import Column, Button, Cancel
from aiogram_dialog.widgets.text import Const

from dialogs.windows.base import KeyboardBuilder
from getters.on_click.admin_keys import on_input_renewal_days
from states import AdminMassRenewal


class AdminMassRenewalSegmentKeyboard(KeyboardBuilder):
    """Клавиатура выбора сегмента для массового продления."""

    def build(self):
        return Column(
            Button(
                Const("⏰ Истекают в 24 часа"),
                id="segment_expiring_24h",
                on_click=self._on_segment_selected,
            ),
            Button(
                Const("📅 Истекают в 7 дней"),
                id="segment_expiring_7d",
                on_click=self._on_segment_selected,
            ),
            Button(
                Const("📆 Истекают в 30 дней"),
                id="segment_expiring_30d",
                on_click=self._on_segment_selected,
            ),
            Button(
                Const("🔴 Истёкшие ключи"),
                id="segment_expired",
                on_click=self._on_segment_selected,
            ),
            Button(
                Const("✅ Активные ключи"),
                id="segment_active",
                on_click=self._on_segment_selected,
            ),
            Button(
                Const("🔹 Все активные ключи"),
                id="segment_all",
                on_click=self._on_segment_selected,
            ),
            Cancel(Const("🔙 Отмена")),
        )

    @staticmethod
    async def _on_segment_selected(callback, button, manager):
        """Обработчик выбора сегмента."""
        # Извлекаем ID сегмента из ID кнопки
        btn_id = button.id
        segment = btn_id.replace("segment_", "")

        manager.dialog_data["selected_segment"] = segment
        await manager.switch_to(AdminMassRenewal.input_days)
        await callback.answer(
            f"✅ Выбран сегмент. Введите количество дней для продления:",
            show_alert=False,
        )
