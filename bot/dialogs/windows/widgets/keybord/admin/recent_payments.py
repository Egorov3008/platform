"""Клавиатура окна платежей за сегодня с переходом к деталям ключа."""

from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Column, Select, SwitchTo, ScrollingGroup
from aiogram_dialog.widgets.text import Const, Format

from dialogs.windows.base import KeyboardBuilder
from states import AdminManager


class RecentPaymentsKeyboard(KeyboardBuilder):
    """Клавиатура платежей за сегодня с кнопками перехода к ключам."""

    async def _on_payment_selected(
        self, callback: CallbackQuery, widget, manager: DialogManager, item_id: str
    ):
        """Обработчик выбора платежа — переход к деталям ключа."""
        payment_keys = manager.dialog_data.get("payment_keys", {})
        key = payment_keys.get(item_id)
        if not key:
            await callback.answer("⚠️ Ключ не найден", show_alert=True)
            return
        manager.dialog_data["selected_key"] = key
        await manager.switch_to(AdminManager.key_details)

    def build(self):
        return Column(
            ScrollingGroup(
                Select(
                    Format("{item[0]}"),
                    id="payment_select",
                    item_id_getter=lambda x: str(x[1]),
                    items="payments_data",
                    on_click=self._on_payment_selected,
                ),
                id="payments_scroll",
                width=1,
                height=5,
            ),
            SwitchTo(
                Const("🔙 Назад"),
                id="back_stats",
                state=AdminManager.static_user,
            ),
        )
