from typing import Any

from aiogram.types import CallbackQuery
from aiogram_dialog import StartMode, DialogManager
from aiogram_dialog.widgets.kbd import Keyboard, Column, Url, Button, Start
from aiogram_dialog.widgets.text import Const, Format

from config import SUPPORT_CHAT_URL
from dialogs.windows.base import KeyboardBuilder
from services.core.payment.router import PaymentRouter
from services.core.data.service import ServiceDataModel
from states import MainMenu
from logger import logger


class PaymentFormKeyboard(KeyboardBuilder):
    """Билдер для формирования клавиатуры при оплате"""

    def __init__(
        self, payment_processor: PaymentRouter, model_service: ServiceDataModel
    ):
        self.payment_processor = payment_processor
        self.model_service = model_service

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
        """Проверяет статус платежа"""
        # payment_id получается из dialog_data
        payment_id = dialog_manager.dialog_data.get("payment_id")

        if not payment_id:
            await callback.answer("⚠️ Платеж не найден", show_alert=True)
            return

        # Проверка на уже обработанный платеж в dialog_data
        if dialog_manager.dialog_data.get("payment_processed"):
            await callback.answer("✅ Платеж уже обработан. Ключ активирован.", show_alert=True)
            return

        # Проверка на блокировку повторного нажатия (processing lock)
        processing_key = f"payment_processing_{payment_id}"
        try:
            is_processing = await dialog_manager.middleware_data.get("cache", {}).get(processing_key)
            if is_processing:
                await callback.answer("⏳ Платеж обрабатывается. Пожалуйста, подождите...", show_alert=False)
                return
            # Устанавливаем lock на 30 секунд
            await dialog_manager.middleware_data.get("cache", {}).set(processing_key, "1", expire=30)
        except Exception:
            # Если кеш недоступен, продолжаем без lock
            pass

        try:
            # Сначала проверяем реальный статус в YooKassa
            from payments.pay_config import YooKassService
            yookassa_service = YooKassService()

            status = await yookassa_service._get_status(payment_id)

            if status == "succeeded":
                # Платеж успешен - обрабатываем
                await self.payment_processor.route(payment_id)
                dialog_manager.dialog_data["payment_processed"] = True
                await callback.answer("✅ Оплата подтверждена! Ключ активирован.", show_alert=True)
            elif status == "pending":
                await callback.answer("⏳ Платеж еще обрабатывается. Пожалуйста, подождите.", show_alert=False)
            elif status == "waiting_for_capture":
                await callback.answer("⏳ Платеж ожидает подтверждения. Обрабатываем...", show_alert=False)
                # Пробуем обработать
                await self.payment_processor.route(payment_id)
                dialog_manager.dialog_data["payment_processed"] = True
            elif status == "canceled":
                await callback.answer("❌ Платеж отменен. Создайте новый.", show_alert=True)
            else:
                # Статус неизвестен или ошибка - пробуем обработать
                await self.payment_processor.route(payment_id)
                dialog_manager.dialog_data["payment_processed"] = True
                await callback.answer("✅ Статус платежа проверен", show_alert=False)

        except ValueError as e:
            # Платеж не найден в БД
            await callback.answer(f"⚠️ {str(e)}", show_alert=True)
        except Exception as e:
            logger.error(
                f"Ошибка при проверке платежа: {e}",
                payment_id=payment_id,
                exc_info=True,
            )
            await callback.answer(
                "❌ Ошибка при проверке платежа. Обратитесь в поддержку.",
                show_alert=True
            )
        finally:
            # Снимаем lock после обработки
            try:
                await dialog_manager.middleware_data.get("cache", {}).delete(processing_key)
            except Exception:
                pass
