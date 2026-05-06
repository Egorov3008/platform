from typing import Any

from aiogram.types import CallbackQuery
from aiogram_dialog import StartMode, DialogManager
from aiogram_dialog.widgets.kbd import Keyboard, Column, Url, Button, Start
from aiogram_dialog.widgets.text import Const, Format

from api.backend_client import BackendAPIClient
from config import SUPPORT_CHAT_URL
from dialogs.windows.base import KeyboardBuilder
from states import MainMenu
from logger import logger


class PaymentFormKeyboard(KeyboardBuilder):
    """Билдер для формирования клавиатуры при оплате"""

    def __init__(self, backend_client: BackendAPIClient):
        self.backend_client = backend_client

    def build(self) -> Keyboard:
        return Column(
            Url(Const(text="Перейти к оплате 💶"), url=Format("{confirmation_url}")),
            Button(
                Const(text="💳 ПРОВЕРИТЬ СТАТУС ОПЛАТЫ"),
                id="paid_for",
                on_click=self._paid_for,
            ),
            Url(Const("💬 Поддержка"), url=Const(SUPPORT_CHAT_URL)),
            Start(
                Const("Назад"),
                id="profile",
                state=MainMenu.main,
                mode=StartMode.RESET_STACK,
            ),
        )

    async def _paid_for(
        self,
        callback: CallbackQuery,
        widget: Any,
        dialog_manager: DialogManager,
        **kwargs,
    ) -> None:
        tg_id = callback.from_user.id
        payment_id = dialog_manager.dialog_data.get("payment_id")

        if not payment_id:
            await callback.answer("⚠️ Платеж не найден", show_alert=True)
            return

        if dialog_manager.dialog_data.get("payment_processed"):
            await callback.answer("✅ Платеж уже обработан. Ключ активирован.", show_alert=True)
            return

        processing_key = f"payment_processing_{payment_id}"
        try:
            cache = dialog_manager.middleware_data.get("cache", {})
            is_processing = await cache.get(processing_key)
            if is_processing:
                await callback.answer("⏳ Платеж обрабатывается. Пожалуйста, подождите...", show_alert=False)
                return
            await cache.set(processing_key, "1", expire=30)
        except Exception:
            pass

        try:
            status = await self.backend_client.get_payment_status(payment_id, tg_id)

            if status == "succeeded":
                dialog_manager.dialog_data["payment_processed"] = True
                await callback.answer("✅ Оплата подтверждена! Ключ активирован.", show_alert=True)
            elif status in ("pending", "waiting_for_capture"):
                await callback.answer("⏳ Платеж еще обрабатывается. Пожалуйста, подождите.", show_alert=False)
            elif status == "canceled":
                await callback.answer("❌ Платеж отменен. Создайте новый.", show_alert=True)
            else:
                await callback.answer("⚠️ Платеж не найден. Обратитесь в поддержку.", show_alert=True)

        except Exception as e:
            logger.error(
                "Ошибка при проверке платежа",
                payment_id=payment_id,
                error=str(e),
                exc_info=True,
            )
            await callback.answer(
                "❌ Ошибка при проверке платежа. Обратитесь в поддержку.",
                show_alert=True,
            )
        finally:
            try:
                await dialog_manager.middleware_data.get("cache", {}).delete(processing_key)
            except Exception:
                pass
