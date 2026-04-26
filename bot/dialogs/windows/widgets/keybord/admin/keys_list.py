"""Клавиатуры для окон списка и деталей ключей админ-панели."""

from typing import Optional

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

from client import XUISession
from dialogs.windows.base import KeyboardBuilder
from states import AdminManager, AdminKeyDeleteSG, AdminKeyChangeDateSG, AdminKeyChangeTariffSG
from services.cache.service import CacheService
from services.cache.key_manager import CacheKeyManager
from services.core.data.service import ServiceDataModel
from services.core.keys.utils.reset import KeyResetter
from services.core.keys.utils.calculator import ExpiryCalculator
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
        """Продлить ключ на 30 дней."""
        selected_key = manager.dialog_data.get("selected_key")

        if not selected_key:
            await callback.answer("❌ Ключ не выбран", show_alert=True)
            return

        try:
            cache: Optional[CacheService] = manager.middleware_data.get("cache")
            xui_session: Optional[XUISession] = manager.middleware_data.get("xui_session")
            container = manager.middleware_data.get("container")

            if not cache:
                await callback.answer("❌ Кеш недоступен", show_alert=True)
                return

            days_to_add = 30

            # Вычислить новую дату истечения с учётом текущего состояния ключа
            if container:
                expiry_calculator: ExpiryCalculator = container.resolve(ExpiryCalculator)
                new_expiry_ms = expiry_calculator.key_duration(selected_key, days_to_add)
            else:
                # Fallback при недоступности контейнера
                new_expiry_ms = selected_key.expiry_time + (days_to_add * 24 * 3600 * 1000)

            # Обновить объект ключа с новой датой истечения
            selected_key.expiry_time = new_expiry_ms

            # Обновить ключ в XUI-панели
            if xui_session:
                try:
                    await xui_session.extend_client_key(selected_key)
                except Exception as xui_error:
                    logger.warning(
                        "Не удалось обновить ключ в XUI-панели при продлении",
                        email=selected_key.email,
                        error=str(xui_error),
                    )
            else:
                logger.warning("XUI-сессия недоступна при продлении ключа", email=selected_key.email)

            # Сохранить обновлённый ключ в кеш
            keys_manager = CacheKeyManager()
            await cache.keys.set(keys_manager.key(selected_key.email), selected_key)

            # Обновить данные в БД через сервисный слой и сбросить флаги
            if container:
                try:
                    pool = container.resolve("asyncpg.Pool")
                    model_data = container.resolve("ServiceDataModel")

                    # Обновляем ключ в БД
                    await model_data.keys.update(pool, selected_key, {"email": selected_key.email})

                    # Сбросить флаги уведомлений и трафик через KeyResetter
                    resetter: KeyResetter = container.resolve(KeyResetter)
                    await resetter.reset_key_after_renewal(pool, selected_key)

                    logger.info(
                        "БД обновлена: expiry_time и флаги сброшены",
                        email=selected_key.email,
                        new_expiry_ms=new_expiry_ms,
                    )
                except Exception as db_error:
                    logger.warning(
                        "Не удалось обновить БД при продлении",
                        email=selected_key.email,
                        error=str(db_error),
                    )

            logger.info(
                f"Ключ {selected_key.email} продлён на {days_to_add} дней администратором"
            )

            await callback.answer(
                f"✅ Ключ {selected_key.email} продлён на {days_to_add} дней",
                show_alert=True,
            )

        except Exception as e:
            logger.error("Ошибка при продлении ключа", error=str(e), exc_info=True)
            await callback.answer(f"❌ Ошибка при продлении: {str(e)}", show_alert=True)