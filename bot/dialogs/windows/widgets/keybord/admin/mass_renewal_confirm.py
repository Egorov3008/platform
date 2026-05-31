"""Клавиатура подтверждения массового продления."""

from typing import Any

from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, StartMode
from aiogram_dialog.widgets.kbd import Button, SwitchTo, Cancel, Column
from aiogram_dialog.widgets.text import Const

from api.backend_client import BackendAPIClient
from dialogs.windows.base import KeyboardBuilder
from logger import logger
from states import AdminManager, AdminMassRenewal


class AdminMassRenewalConfirmKeyboard(KeyboardBuilder):
    """Клавиатура подтверждения массового продления."""

    def build(self):
        return Column(
            Button(
                Const("✅ Подтвердить продление"),
                id="confirm_mass_renewal",
                on_click=self._on_confirm,
            ),
            SwitchTo(
                Const("🔙 Отмена"),
                id="cancel_mass_renewal",
                state=AdminMassRenewal.select_segment,
            ),
            Cancel(Const("🚪 Выход")),
        )

    @staticmethod
    async def _on_confirm(
        callback: CallbackQuery,
        button: Any,
        manager: DialogManager,
        **kwargs,
    ):
        """Подтвердить массовое продление через backend API."""
        try:
            keys_to_renew = manager.dialog_data.get("keys_to_renew", [])
            days = manager.dialog_data.get("renewal_days", 0)

            if not keys_to_renew or not days:
                await callback.answer(
                    "❌ Нет данных для продления",
                    show_alert=True,
                )
                return

            container = manager.middleware_data.get("container")
            if not container:
                await callback.answer("❌ Сервисы недоступны", show_alert=True)
                return

            backend = container.resolve(BackendAPIClient)

            await callback.message.answer(
                f"⏳ Начинаю массовое продление {len(keys_to_renew)} ключей на {days} дней..."
            )

            emails = [k.email for k in keys_to_renew]
            result = await backend.admin_mass_renew(emails=emails, days=days)

            success = result.get("success", 0)
            failed = result.get("failed", 0)
            report_text = f"<b>Массовое продление завершено</b>\n\n✅ Успешно: {success}\n❌ Ошибки: {failed}"
            if failed > 0:
                details = result.get("results", [])
                errs = [f"• {r['email']}: {r.get('error', 'unknown')}" for r in details if not r.get("success")]
                if errs:
                    report_text += "\n\nОшибки:\n" + "\n".join(errs[:10])

            await callback.message.answer(report_text, parse_mode="HTML")
            await callback.answer("✅ Массовое продление завершено", show_alert=True)

            await manager.start(
                AdminManager.main,
                mode=StartMode.RESET_STACK,
            )

        except Exception as e:
            logger.error(
                "Ошибка при массовом продлении",
                error=str(e),
                exc_info=True,
            )
            await callback.answer(
                f"❌ Ошибка: {str(e)}",
                show_alert=True,
            )
