from dataclasses import dataclass
from typing import Dict, Any, Optional, Protocol

from aiogram_dialog import DialogManager

from dialogs.windows.base import DataGetter
from models import Tariff
from services.core.data.service import ServiceDataModel
from services.core.price.result import PriceResult, apply_volume_discount
from logger import logger
from states import MainMenu

MIN_PAYMENT_AMOUNT = 10.0


class PriceCalculatorProtocol(Protocol):
    """Протокол для сервиса расчёта цены."""
    async def calculate(self, tg_id: int, tariff: Tariff) -> PriceResult: ...


@dataclass
class PaymentContext:
    """Неизменяемый контекст расчёта платежа. Извлечён из dialog_manager."""
    payment_type: str
    tariff: Tariff
    number_of_months: int
    amount: float
    discounted_amount: Optional[float]

    def __post_init__(self):
        if not self.payment_type:
            raise ValueError("Отсутствует payment_type")
        if self.tariff is None:
            raise ValueError("Отсутствует tariff")

    @property
    def has_precomputed_discount(self) -> bool:
        """True, если скидка уже была вычислена (например, TariffPreviewGetter)."""
        logger.debug("Проверка скидки", has_precomputed_discount=self.discounted_amount is not None)
        return self.discounted_amount is not None

    @property
    def base_price(self) -> float:
        """Возвращает эффективную цену: скидочную если доступна, иначе оригинальную."""
        return float(self.discounted_amount) if self.has_precomputed_discount else float(self.amount)


class SettingsPayment(DataGetter):
    def __init__(self, price_service: PriceCalculatorProtocol, model_data: ServiceDataModel):
        super().__init__()
        self.price_service = price_service
        self.model_data = model_data

    async def get_data(self, dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
        payment_type = None
        tg_id = dialog_manager.event.from_user.id
        try:
            context = self._extract_context(dialog_manager)
            price_per_month = await self._resolve_price_per_month(tg_id, context)

            # Применяем скидку за объём поверх Stock-скидки
            final_with_volume, total_without_volume, volume_percent = apply_volume_discount(
                price_per_month, context.number_of_months
            )

            # Реферальная скидка (третий слой)
            referral_discount = 0.0
            user_balance = 0.0
            user = await self.model_data.users.get_data(tg_id)
            if user and user.balance > 0 and final_with_volume > MIN_PAYMENT_AMOUNT:
                user_balance = user.balance
                max_discount = round(final_with_volume - MIN_PAYMENT_AMOUNT, 2)
                referral_discount = round(min(user_balance, max_discount), 2)

            final_amount = round(final_with_volume - referral_discount, 2)

            self._persist(
                dialog_manager, context, final_amount, price_per_month,
                volume_percent, referral_discount, user_balance,
            )

            logger.info(
                "[Цена:SettingsPay] Итог формирования",
                tg_id=tg_id,
                final_amount=final_amount,
                number_of_months=context.number_of_months,
                payment_type=context.payment_type,
                volume_discount_percent=volume_percent,
                referral_discount=referral_discount,
            )

            return {
                "tariff_name": context.tariff.name_tariff,
                "number_of_months": context.number_of_months,
                "amount": final_amount,
                "amount_without_volume_discount": total_without_volume,
                "volume_discount_percent": volume_percent,
                "has_volume_discount": volume_percent > 0,
                "referral_discount": referral_discount,
                "has_referral_discount": referral_discount > 0,
            }
        except Exception as e:
            logger.error(
                "При формировании параметров оплаты возникла ошибка",
                error_type=type(e).__name__,
                error_message=str(e),
                tg_id=tg_id,
                payment_type=payment_type,
                exc_info=True,
            )
            await dialog_manager.start(MainMenu.main)
            await dialog_manager.event.answer(
                "При формировании платежа возникла ошибка, обратитесь в поддержку"
            )
            return {}

    def _extract_context(self, dialog_manager: DialogManager) -> PaymentContext:
        """
        Извлекает контекст платежа из dialog_manager без побочных эффектов.
        Вызывает ValueError если отсутствуют требуемые поля.
        """
        raw = dialog_manager.dialog_data or dialog_manager.start_data

        logger.debug(
            "[Цена:SettingsPay] Извлечение контекста платежа",
            payment_type=raw.get("payment_type"),
            has_discounted=bool(raw.get("discounted_amount")),
            number_of_months=raw.get("number_of_months", 1),
        )

        return PaymentContext(
            payment_type=raw.get("payment_type"),
            tariff=raw.get("tariff"),
            number_of_months=raw.get("number_of_months", 1),
            amount=float(raw.get("amount", 0)),
            discounted_amount=raw.get("discounted_amount"),
        )

    async def _resolve_price_per_month(self, tg_id: int, context: PaymentContext) -> float:
        """
        Вычисляет цену за 1 месяц (со Stock-скидкой, если есть).
        Скидка за объём применяется отдельно в get_data().
        """
        if context.has_precomputed_discount:
            logger.debug(
                "[Цена:SettingsPay] Использование предвычисленной скидки",
                discounted_amount=context.discounted_amount,
                number_of_months=context.number_of_months,
            )
            return context.base_price

        # Прямой вход без предвычисленной скидки — расчитать скидку Stock
        result = await self.price_service.calculate(tg_id, context.tariff)
        if result.has_discount:
            logger.info(
                "[Цена:SettingsPay] Скидка Stock применена",
                tg_id=tg_id,
                original_amount=result.original_amount,
                discounted_amount=result.final_amount,
                stock_type=result.stock_type,
                stock_value=result.stock_value,
            )
            return float(result.final_amount)

        return context.base_price

    def _persist(
        self, dialog_manager: DialogManager, context: PaymentContext,
        final_amount: float, price_per_month: float, discount_percent: int = 0,
        referral_discount: float = 0.0, user_referral_balance: float = 0.0,
    ) -> None:
        """
        Сохраняет контекст платежа и итоговую сумму в dialog_data.
        Единая ответственность: только запись данных, без расчётов.
        """
        # discounted_amount хранит помесячную цену (со Stock-скидкой, но БЕЗ скидки за объём),
        # чтобы _months_changed мог корректно пересчитать итог при изменении количества месяцев
        discounted_per_month = price_per_month

        logger.info(
            "[Цена:SettingsPay] Данные перезаписаны",
            discounted_amount=discounted_per_month,
            amount=final_amount,
            number_of_months=context.number_of_months,
            payment_type=context.payment_type,
            discount_percent=discount_percent,
            referral_discount=referral_discount,
        )

        dialog_manager.dialog_data["payment_type"] = context.payment_type
        dialog_manager.dialog_data["number_of_months"] = context.number_of_months
        dialog_manager.dialog_data["amount"] = final_amount
        dialog_manager.dialog_data["tariff"] = context.tariff
        dialog_manager.dialog_data["discounted_amount"] = discounted_per_month
        dialog_manager.dialog_data["discount_percent"] = discount_percent
        dialog_manager.dialog_data["referral_discount"] = referral_discount
        dialog_manager.dialog_data["user_referral_balance"] = user_referral_balance
