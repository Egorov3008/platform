from typing import Any

from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Counter, SwitchTo, Cancel, ManagedCounter
from aiogram_dialog.widgets.text import Const

from dialogs.windows.base import KeyboardBuilder
from logger import logger
from services.core.price.result import apply_volume_discount
from states.payment import PaymentState

MIN_PAYMENT_AMOUNT = 10.0


class SettingPaymentKeyboard(KeyboardBuilder):
    async def _months_changed(
        self, event: Any, widget: ManagedCounter, dialog_manager: DialogManager
    ):
        # Получаем тариф и скидочную цену (per-month, без скидки за объём)
        tariff_data = dialog_manager.dialog_data.get(
            "tariff"
        ) or dialog_manager.start_data.get("tariff")
        discounted_amount = dialog_manager.dialog_data.get("discounted_amount")

        number_of_months = dialog_manager.current_context().widget_data.get(
            "number_of_months"
        )
        dialog_manager.dialog_data["number_of_months"] = number_of_months

        # Используем скидочную цену, если доступна, иначе берем из тарифа
        amount_per_month = discounted_amount or (
            tariff_data.amount if tariff_data else 0
        )

        # Применяем скидку за объём
        final_total, _, volume_percent = apply_volume_discount(
            float(amount_per_month), number_of_months
        )

        # Реферальная скидка
        user_balance = dialog_manager.dialog_data.get("user_referral_balance", 0.0)
        referral_discount = 0.0
        if user_balance > 0 and final_total > MIN_PAYMENT_AMOUNT:
            max_discount = round(final_total - MIN_PAYMENT_AMOUNT, 2)
            referral_discount = round(min(user_balance, max_discount), 2)
            final_total = round(final_total - referral_discount, 2)
        dialog_manager.dialog_data["referral_discount"] = referral_discount

        dialog_manager.dialog_data["amount"] = final_total

        logger.info(
            "[Цена:MonthsChanged] Пересчёт суммы",
            number_of_months=number_of_months,
            discounted_amount_per_month=discounted_amount,
            tariff_amount=tariff_data.amount if tariff_data else None,
            amount_per_month_used=amount_per_month,
            final_total=final_total,
            volume_discount_percent=volume_percent,
            referral_discount=referral_discount,
        )

    def build(self):
        return (
            Counter(
                id="number_of_months",
                max_value=6,
                min_value=1,
                on_value_changed=self._months_changed,
                default=1,
            ),
            SwitchTo(Const("💳 Оплатить"), id="done", state=PaymentState.form_pay),
            Cancel(Const("Назад")),
        )
