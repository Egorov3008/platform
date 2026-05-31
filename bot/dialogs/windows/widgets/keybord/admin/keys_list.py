"""Клавиатуры для окон списка и деталей ключей админ-панели."""

from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import (
    Column,
    Button,
    SwitchTo,
    ScrollingGroup,
    PrevPage,
    NextPage,
    Row,
    Cancel,
)
from aiogram_dialog.widgets.text import Const

from api.backend_client import BackendAPIClient
from dialogs.windows.base import KeyboardBuilder
from states import AdminManager, AdminKeyDeleteSG, AdminKeyChangeDateSG, AdminKeyChangeTariffSG
from logger import logger

from widgets.keybord import key_selector


class AdminKeysListKeyboard(KeyboardBuilder):
    """Клавиатура для окна списка ключей с сегментацией."""

    def build(self):
        return (Column(
            ScrollingGroup(
                key_selector(),
                id="keys_list",
                width=1,
                height=5,  # 5 ключей на странице
                hide_pager=True,
            )),Row(
                PrevPage(
                    scroll="keys_list",
                    text=Const("⬅️  Назад"),
                ),
                NextPage(
                    scroll="keys_list",
                    text=Const("Вперед ➡️ "),
                ),
            ),SwitchTo(
                Const("🔙 Назад в панель"),
                id="back_to_stats",
                state=AdminManager.static_user,
            )
            )
        


class AdminKeyDetailsKeyboard(KeyboardBuilder):
    """Клавиатура для окна деталей ключа с кнопками администрирования."""

    def build(self):
        return Column(
            Button(
                Const("❌ Удалить ключ"),
                id="delete",
                on_click=self._to_delete,
            ),
            Button(
                Const("⏳ Продлить ключ на месяц"), id="renew_key", on_click=self._on_renew_key
            ),
            Button(
                Const("📅 Изменить дату истечения"),
                id="change_date",
                on_click=self._to_change_date,
            ),
            Button(
                Const("🔄 Изменить тариф"),
                id="change_tariff",
                on_click=self._to_change_tariff,
            ),
            Cancel(
                Const("🔙 Назад к списку"),
                id="back_to_list"
            ),
        )

    @staticmethod
    async def _to_delete(callback: CallbackQuery, _button, manager: DialogManager):
        """Открыть диалог удаления ключа."""
        selected_key = manager.dialog_data.get("selected_key")
        if selected_key:
            await manager.start(AdminKeyDeleteSG.confirm, data={"email": selected_key.email})

    @staticmethod
    async def _to_change_date(callback: CallbackQuery, _button, manager: DialogManager):
        """Открыть диалог изменения даты истечения."""
        selected_key = manager.dialog_data.get("selected_key")
        logger.debug("Изменнение даты истечения подписки", selected_key=selected_key is None)
        
        if selected_key:
            await manager.start(AdminKeyChangeDateSG.pick_date, data={"email": selected_key.email})
        else:
            await callback.answer("Ключ не выбран", show_alert=True)

    @staticmethod
    async def _to_change_tariff(callback: CallbackQuery, _button, manager: DialogManager):
        """Открыть диалог изменения тарифа."""
        selected_key = manager.dialog_data.get("selected_key")
        if selected_key:
            await manager.start(AdminKeyChangeTariffSG.pick_tariff, data={"email": selected_key.email})

    @staticmethod
    async def _on_renew_key(callback: CallbackQuery, button, manager: DialogManager):
        """Продлить ключ на 30 дней через backend API."""
        selected_key = manager.dialog_data.get("selected_key")

        if not selected_key:
            await callback.answer("❌ Ключ не выбран", show_alert=True)
            return

        try:
            container = manager.middleware_data.get("container")
            if not container:
                await callback.answer("❌ Сервис недоступен", show_alert=True)
                return

            backend = container.resolve(BackendAPIClient)
            days_to_add = 30

            # Вычислить новую дату истечения
            from datetime import datetime, timezone
            now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
            old_expiry = selected_key.expiry_time
            base_expiry = max(old_expiry, now_ms)
            new_expiry_ms = base_expiry + (days_to_add * 24 * 3600 * 1000)

            success = await backend.admin_change_key_date(selected_key.email, new_expiry_ms)
            if not success:
                await callback.answer("❌ Не удалось продлить ключ", show_alert=True)
                return

            logger.info(
                "Ключ продлён администратором через backend",
                email=selected_key.email,
                days=days_to_add,
            )
            await callback.answer(
                f"✅ Ключ {selected_key.email} продлён на {days_to_add} дней",
                show_alert=True,
            )

        except Exception as e:
            logger.error("Ошибка при продлении ключа", error=str(e), exc_info=True)
            await callback.answer(f"❌ Ошибка при продлении: {str(e)}", show_alert=True)