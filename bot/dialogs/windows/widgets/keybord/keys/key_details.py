from typing import Optional

from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Column, CopyText, Url, SwitchTo, Button, Back
from aiogram_dialog.widgets.text import Const, Format

from api.backend_client import BackendAPIClient
from config import SUPPORT_CHAT_URL, DOWNLOAD_IOS, DOWNLOAD_ANDROID
from dialogs.windows.base import KeyboardBuilder
from models import Tariff
from services.core.data.service import ServiceDataModel
from states.key import KeysInit
from states.payment import PaymentState


class KeyDetailsKeyboard(KeyboardBuilder):
    """Клавиатура окна детального просмотра ключа."""

    def __init__(self, model_data: ServiceDataModel, backend_client: BackendAPIClient):
        self.tariff_data = model_data.tariffs
        self._backend = backend_client

    async def _on_trial_renewal_click(
        self,
        callback: CallbackQuery,
        button: Button,
        dialog_manager: DialogManager,
        **kwargs,
    ):
        """Обработка продления trial-ключа — переход на PaymentState"""
        email = dialog_manager.dialog_data.get("email")
        if not email:
            await callback.answer("❌ Email не найден", show_alert=True)
            return

        await dialog_manager.start(PaymentState.view_tariff, data={"email": email})

    async def _on_renewal_click(
        self,
        callback: CallbackQuery,
        button: Button,
        dialog_manager: DialogManager,
        **kwargs,
    ):
        """Обработка продления paid-ключа — переход на PaymentState.setting_pay"""
        email = dialog_manager.dialog_data.get("email")
        if not email:
            await callback.answer("❌ Email не найден", show_alert=True)
            return

        key_data = await self._backend.get_key_details(email)
        if not key_data:
            await callback.answer("❌ Ключ не найден", show_alert=True)
            return

        tariff: Optional[Tariff] = await self.tariff_data.get_data(key_data.get("tariff_id"))

        await dialog_manager.start(
            PaymentState.setting_pay,
            data={
                "email": email,
                "payment_type": f"renew_key|{email}",
                "amount": float(tariff.amount if tariff else 0),
                "tariff": tariff,
            },
        )

    def build(self):
        return Column(
            CopyText(Const("📋 Скопировать ключ"), copy_text=Format("{keys}"), when="not_error"),
            Url(Const("🍏 Скачать для iPhone"), url=Const(DOWNLOAD_IOS)),
            Url(Const("🤖 Скачать для Android"), url=Const(DOWNLOAD_ANDROID)),
            Button(
                Const("⌛ Продлить ключ"),
                id="extend_trial",
                when="is_trial",
                on_click=self._on_trial_renewal_click,
            ),
            Button(
                Const("⌛ Продлить ключ"),
                id="extend_paid",
                when="not_trial_tariff",
                on_click=self._on_renewal_click,
            ),
            SwitchTo(
                Const("❌ Удалить ключ"),
                id="delete_key",
                state=KeysInit.confirmation_delete_key,
            ),
            Url(Const("💬 Поддержка"), url=Const(SUPPORT_CHAT_URL)),
            Back(Const("Назад"), id="back_key"),
        )
