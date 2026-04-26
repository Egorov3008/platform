"""Клавиатура для изменения тарифа ключа."""

import asyncio
from typing import Any, Optional

import asyncpg
from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, StartMode
from aiogram_dialog.widgets.kbd import (
    Column,
    Button,
    Cancel,
    Select,
    SwitchTo,
)
from aiogram_dialog.widgets.text import Const, Format

from dialogs.windows.base import KeyboardBuilder
from logger import logger
from services.cache.key_manager import CacheKeyManager
from services.core.data.service import ServiceDataModel
from services.core.keys.utils.reset import KeyResetter
from client import XUISession
from models import Key, Tariff
from states import AdminKeyChangeTariffSG, AdminManager


class AdminKeyChangeTariffKeyboard(KeyboardBuilder):
    """Клавиатура выбора тарифа (pick_tariff state)."""

    def build(self):
        return Column(
            Select(
                Format("{item[1].name_tariff} ({item[1].amount}₽)"),
                id="s_tariff",
                items="tariff_list",
                item_id_getter=lambda x: str(x[0]),
                on_click=self._on_tariff_selected,
            ),
            Cancel(Const("🔙 Назад")),
        )

    @staticmethod
    async def _on_tariff_selected(
        callback: CallbackQuery,
        widget: Any,
        manager: DialogManager,
        item_id: str,
    ):
        """Обработчик выбора тарифа."""
        try:
            # Сохранить выбранный тариф в dialog_data
            manager.dialog_data["selected_tariff_id"] = int(item_id)
            # Перейти на окно подтверждения
            await manager.switch_to(AdminKeyChangeTariffSG.confirm)
            await callback.answer("✅ Тариф выбран", show_alert=False)
        except Exception as e:
            logger.error("Ошибка при выборе тарифа", error=str(e), exc_info=True)
            await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


class AdminKeyChangeTariffConfirmKeyboard(KeyboardBuilder):
    """Клавиатура подтверждения изменения тарифа (confirm state)."""

    def build(self):
        return Column(
            Button(
                Const("✅ Подтвердить"),
                id="confirm_tariff",
                on_click=self._on_confirm,
            ),
            SwitchTo(
                Const("🔄 Выбрать другой тариф"),
                id="back_tariff",
                state=AdminKeyChangeTariffSG.pick_tariff,
            ),
            Cancel(Const("🔙 Отмена")),
        )

    @staticmethod
    async def _on_confirm(
        callback: CallbackQuery,
        button: Any,
        manager: DialogManager,
        **kwargs,
    ):
        """Подтвердить изменение тарифа."""
        email = manager.start_data.get("email")
        selected_tariff_id = manager.dialog_data.get("selected_tariff_id")

        if not email or not selected_tariff_id:
            await callback.answer("❌ Некорректные данные", show_alert=True)
            return

        try:
            # Получить зависимости
            cache = manager.middleware_data.get("cache")
            xui_session: XUISession = manager.middleware_data.get("xui_session")

            if not cache or not xui_session:
                await callback.answer("❌ Сервис недоступен", show_alert=True)
                return

            # Получить ключ и новый тариф из кеша
            key: Optional[Key] = await cache.keys.get(CacheKeyManager.key(email))
            new_tariff: Optional[Tariff] = await cache.tariffs.get(
                CacheKeyManager.tariff(selected_tariff_id)
            )

            if not key or not new_tariff:
                await callback.answer("❌ Ключ или тариф не найдены", show_alert=True)
                return

            # Получить контейнер и сервис данных
            container = manager.middleware_data.get("container")
            if not container:
                await callback.answer("❌ Контейнер не инициализирован", show_alert=True)
                return
            model_data: ServiceDataModel = container.resolve(ServiceDataModel)
            pool: asyncpg.Pool = container.resolve(asyncpg.Pool)

            # Обновить параметры ключа с новым тарифом
            key.tariff_id = new_tariff.id
            key.total_gb = new_tariff.traffic_limit
            key.limit_ip = new_tariff.limit_ip
            key.name_tariff = new_tariff.name_tariff

            # Обновить в XUI, DB и кеше параллельно
            logger.debug("Обновление тарифа ключа", email=email, new_tariff_id=selected_tariff_id)
            results = await asyncio.gather(
                xui_session.extend_client_key(key),
                model_data.keys.update(pool, key, {"email": key.email}),
                cache.keys.set(CacheKeyManager.key(email), key),
                return_exceptions=True,
            )

            errors = [r for r in results if isinstance(r, Exception)]
            if errors:
                logger.error("Ошибки при обновлении тарифа ключа", email=email, errors=errors)

            # Сбросить флаги уведомлений и трафик через KeyResetter
            resetter: KeyResetter = container.resolve(KeyResetter)
            await resetter.reset_key_after_renewal(pool, key)

            logger.info(
                "Тариф ключа обновлён",
                email=email,
                new_tariff=new_tariff.name_tariff
            )
            await callback.answer(
                f"✅ Тариф изменён на {new_tariff.name_tariff}",
                show_alert=True,
            )

            # Вернуться к деталям ключа с обновлёнными данными
            await manager.start(
                AdminManager.key_details,
                data={"selected_key": key},
                mode=StartMode.RESET_STACK,
            )

        except Exception as e:
            logger.error(
                "Ошибка при обновлении тарифа ключа",
                email=email,
                error=str(e),
                exc_info=True,
            )
            await callback.answer(
                f"❌ Ошибка при обновлении: {str(e)}", show_alert=True
            )
