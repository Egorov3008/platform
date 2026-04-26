"""Keyboard builder для окна статистики платежей."""

from aiogram_dialog.widgets.kbd import Column, SwitchTo, Button
from aiogram_dialog.widgets.text import Const

from dialogs.windows.base import KeyboardBuilder
from states import AdminManager


class PaymentStatsKeyboard(KeyboardBuilder):
    """Клавиатура для окна статистики платежей."""

    async def _on_refresh_forecast(self, callback, button, manager):
        """Обработчик обновления прогноза."""
        try:
            # Просто перезапускаем текущее состояние — getter обновит данные
            await manager.switch_to(AdminManager.payment_stats)
        except Exception:
            await callback.answer("⚠️ Ошибка при обновлении", show_alert=True)

    def build(self):
        return Column(
            Button(
                Const("🔄 Обновить прогноз"),
                id="refresh_forecast",
                on_click=self._on_refresh_forecast,
            ),
            SwitchTo(
                Const("🔙 Назад"),
                id="back_to_main",
                state=AdminManager.main,
            ),
        )
