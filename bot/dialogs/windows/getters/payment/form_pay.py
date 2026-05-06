from typing import Optional

from aiogram_dialog import DialogManager

from api.backend_client import BackendAPIClient
from dialogs.windows.base import DataGetter
from logger import logger


class FormPaymentGetter(DataGetter):
    """Getter для окна оплаты — создаёт платёж через backend API."""

    def __init__(self, backend_client: BackendAPIClient):
        self.backend_client = backend_client
        self._data = {}

    async def get_data(self, dialog_manager: DialogManager, **kwargs) -> dict:
        self._get_payment_data(dialog_manager)
        tg_id = dialog_manager.event.from_user.id
        amount: Optional[float] = self._data.get("amount")
        if not amount:
            raise ValueError("Не указана сумма оплаты")

        existing_payment_id = dialog_manager.dialog_data.get("payment_id")
        existing_confirmation_url = dialog_manager.dialog_data.get("confirmation_url")

        if existing_payment_id and existing_confirmation_url:
            status = await self.backend_client.get_payment_status(existing_payment_id, tg_id)
            if status in ("pending", "waiting_for_capture", None):
                logger.info(
                    "[Цена:FormPay] Используется существующий платёж",
                    tg_id=tg_id,
                    payment_id=existing_payment_id,
                    status=status,
                )
                return {"confirmation_url": existing_confirmation_url}

        payment_type: str = self._data.get("payment_type", "")
        tariff = self._data.get("tariff")
        number_of_months: int = self._data.get("number_of_months", 1)

        if payment_type.startswith("renew_key|"):
            operation = "renew_key"
            email = payment_type.split("|", 1)[1]
        else:
            operation = "create_key"
            email = None

        tariff_id: Optional[int] = tariff.id if tariff else None
        if tariff_id is None and "|" in payment_type:
            try:
                tariff_id = int(payment_type.split("|", 1)[1])
            except ValueError:
                pass

        if tariff_id is None:
            raise ValueError("Не удалось определить тариф для создания платежа")

        payment_data = await self.backend_client.create_payment(
            tg_id=tg_id,
            tariff_id=tariff_id,
            operation=operation,
            number_of_months=number_of_months,
            email=email,
            amount=amount,
        )
        if not payment_data:
            raise ValueError("Не удалось создать платёж. Обратитесь в поддержку.")

        payment_id = payment_data["payment_id"]
        confirmation_url = payment_data["confirmation_url"]

        dialog_manager.dialog_data["payment_id"] = payment_id
        dialog_manager.dialog_data["confirmation_url"] = confirmation_url

        logger.info(
            "[Цена:FormPay] Платёж создан через backend",
            tg_id=tg_id,
            payment_id=payment_id,
            amount=amount,
            number_of_months=number_of_months,
            payment_type=payment_type,
        )

        return {"confirmation_url": confirmation_url}

    def _get_payment_data(self, dialog_manager: DialogManager) -> None:
        self._data = dialog_manager.dialog_data or dialog_manager.start_data
