from typing import Any

import asyncpg
from aiogram_dialog import DialogManager

from dialogs.windows.base import DataGetter
from models import PaymentModel
from payments.pay_config import YooKassService
from services.core.data.service import ServiceDataModel
from logger import logger


class FormPaymentGetter(DataGetter):
    """Класс getter для работы с окном оплаты"""

    def __init__(
        self,
        service: YooKassService,
        model_service: ServiceDataModel,
        conn: asyncpg.Pool,
    ):
        self.service = service
        self.conn = conn
        self.payment_data = model_service.payments
        self._data = {}

    async def get_data(self, dialog_manager: DialogManager, **kwargs) -> dict:
        """Основной метод"""
        self._get_payment_data(dialog_manager)
        tg_id = dialog_manager.event.from_user.id
        amount = self._data.get("amount")
        if not amount:
            raise ValueError("Не указана сумма оплаты")
        
        # Проверяем, есть ли уже payment_id в dialog_data
        existing_payment_id = dialog_manager.dialog_data.get("payment_id")
        
        if existing_payment_id:
            # Платеж уже создан - проверяем его статус в YooKassa
            try:
                status = await self.service._get_status(existing_payment_id)
                if status in ("pending", "waiting_for_capture"):
                    # Платеж еще не завершен - возвращаем существующий
                    logger.info(
                        "[Цена:FormPay] Используется существующий платёж",
                        tg_id=tg_id,
                        payment_id=existing_payment_id,
                        status=status,
                    )
                    # Получаем URL подтверждения из БД или кэша
                    confirmation_url = await self._get_confirmation_url(existing_payment_id)
                    if confirmation_url:
                        return {"confirmation_url": confirmation_url}
            except Exception as e:
                logger.warning(
                    "[Цена:FormPay] Ошибка проверки статуса платежа",
                    payment_id=existing_payment_id,
                    error=str(e),
                )
        
        # Создаем новый платеж
        description = f"Оплата ИТ-услуг для {tg_id}"
        payment_data: dict = await self.service.create_payment_form(
            amount, description=description
        )
        payment_id = payment_data.get("payment_id")
        confirmation_url = payment_data.get("confirmation_url")

        dialog_manager.dialog_data["payment_id"] = payment_id

        await self.seter(payment_id, tg_id, amount)

        logger.info(
            "[Цена:FormPay] Платёж создан в YooKassa",
            tg_id=tg_id,
            payment_id=payment_id,
            amount=amount,
            number_of_months=self._data.get("number_of_months", 1),
            payment_type=self._data.get("payment_type"),
        )

        return {"confirmation_url": confirmation_url}
    
    async def _get_confirmation_url(self, payment_id: str) -> str | None:
        """Получает URL подтверждения платежа из БД или кэша."""
        try:
            # Пытаемся получить данные платежа из БД
            payment = await self.payment_data.get_data(payment_id)
            if payment and hasattr(payment, 'confirmation_url'):
                return payment.confirmation_url
        except Exception:
            pass
        return None

    def _get_payment_data(self, dialog_manager: DialogManager) -> Any:
        """Возвращает данные для диалога оплаты"""
        self._data = dialog_manager.dialog_data or dialog_manager.start_data

    async def seter(self, payment_id: str, user_id: int, amount: float) -> None:

        payment = PaymentModel(
            payment_id=payment_id,
            payment_type=self._data.get("payment_type"),
            tg_id=user_id,
            amount=amount,
            number_of_months=self._data.get("number_of_months", 1),
            discount_percent=self._data.get("discount_percent", 0),
            referral_discount=self._data.get("referral_discount", 0.0),
            status="pending",
        )
        await self.payment_data.save_data(self.conn, payment, payment_id=payment_id)
