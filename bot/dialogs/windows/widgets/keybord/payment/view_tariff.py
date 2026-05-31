from typing import Optional
from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, ShowMode
from aiogram_dialog.widgets.kbd import Column, Select, Cancel
from aiogram_dialog.widgets.text import Const
from dialogs.windows.base import GenericSelectBuilder, KeyboardBuilder
from logger import logger
from models import Tariff
from states.payment import PaymentState


class TariffSelectBuilder(KeyboardBuilder):
    """"""

    async def _on_tariff_selected(
        self,
        callback: CallbackQuery,
        widget: Select,
        dialog_manager: DialogManager,
        item_id: str,
    ):
        """Обработчик выбора тарифа — специфичен для платежей"""

        data = dialog_manager.dialog_data
        start_data = dialog_manager.start_data or {}

        processed_tariffs = data.get("processed_tariffs", {})
        tariff_data = processed_tariffs.get(item_id)

        if not tariff_data:
            await callback.answer("❌ Тарифы не найден", show_alert=True)
            return

        if isinstance(tariff_data, dict):
            tariff: Optional[Tariff] = tariff_data.get("tariff")
            amount = tariff_data.get("discounted_amount") or (
                tariff.amount if tariff else 0
            )
        else:
            # Для обратной совместимости, если tariff передается напрямую
            tariff = tariff_data
            amount = tariff.amount if tariff else 0  # type: ignore

        # Поддержка email из start_data (при переходе из KeyDetails)
        email = (
            data.get("email") or start_data.get("email")
            if data
            else start_data.get("email")
        )

        payment_type = f"renew_key|{email}" if email else f"create_key|{item_id}"
        logger.info(
            "[Цена:TariffSelect] Тариф выбран",
            tariff_id=item_id,
            tariff_name=tariff.name_tariff if tariff else None,
            original_amount=tariff.amount if tariff else None,
            discounted_amount=amount,
            payment_type=payment_type,
        )

        update = {
            "amount": amount,
            "tariff": tariff,
            "payment_type": payment_type,
        }
        if tariff_data.get("discounted_amount") is not None:
            update["discounted_amount"] = tariff_data["discounted_amount"]

        dialog_manager.dialog_data.update(update)

        # Для продления ключа сохраняем выбранный tariff_id в dialog_data
        if email:
            dialog_manager.dialog_data[f"renewal_tariff_{email}"] = int(item_id)
            logger.info(
                "[Цена:TariffSelect] Выбранный тариф сохранён в dialog_data для продления",
                email=email,
                tariff_id=item_id,
            )

        await dialog_manager.switch_to(
            PaymentState.setting_pay, show_mode=ShowMode.EDIT
        )

    def build(self) -> Column:
        """Возвращает универсальный Select, настроенный под тарифы"""
        return Column(
            GenericSelectBuilder(
                id="s_tariffs",
                items_key="tariff_list",
                text_format="{item[0]}",  # Например: ("Тариф Pro", "pro")
                item_id_getter=lambda x: x[1],  # ID из второго элемента кортежа
                on_click=self._on_tariff_selected,
            ).build(),
            Cancel(Const("Назад")),
        )
