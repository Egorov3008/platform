"""Клавиатура для изменения даты истечения ключа."""

import asyncio
import calendar
from datetime import datetime, timezone
from typing import Any, Optional

import asyncpg
from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, StartMode
from aiogram_dialog.widgets.kbd import (
    Column,
    Button,
    Cancel,
    Calendar,
    CalendarConfig,
    SwitchTo,
)
from aiogram_dialog.widgets.text import Const

from dialogs.windows.base import KeyboardBuilder
from logger import logger
from services.cache.key_manager import CacheKeyManager
from services.core.data.service import ServiceDataModel
from services.conteiner.app import get_container
from services.core.keys.utils.reset import KeyResetter
from client import XUISession
from models import Key
from states import AdminKeyChangeDateSG, AdminManager


class AdminKeyChangeDateKeyboard(KeyboardBuilder):
    """Клавиатура выбора даты истечения ключа (pick_date state)."""

    def build(self):
        return Calendar(
                id="calendar",
                on_click=self._on_date_selected,
                config=CalendarConfig(firstweekday=calendar.SUNDAY),
            ),Cancel(Const("🔙 Назад"))

    @staticmethod
    async def _on_date_selected(
        callback: CallbackQuery,
        widget: Calendar,
        manager: DialogManager,
        selected_date: datetime,
    ):
        """Обработчик выбора даты в календаре."""
        try:
            # Сохранить выбранную дату в dialog_data
            manager.dialog_data["selected_date"] = selected_date
            # Перейти на окно подтверждения
            await manager.switch_to(AdminKeyChangeDateSG.confirm)
        except Exception as e:
            logger.error("Ошибка при выборе даты", error=str(e), exc_info=True)
            if callback:
                await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


class AdminKeyChangeDateConfirmKeyboard(KeyboardBuilder):
    """Клавиатура подтверждения изменения даты (confirm state)."""

    def build(self):
        return Column(
            Button(
                Const("✅ Подтвердить"),
                id="confirm_date",
                on_click=self._on_confirm,
            ),
            SwitchTo(
                Const("📅 Выбрать другую дату"),
                id="back_date",
                state=AdminKeyChangeDateSG.pick_date,
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
        """Подтвердить изменение даты истечения."""
        email = manager.start_data.get("email")
        selected_date = manager.dialog_data.get("selected_date")

        if not email or not selected_date:
            await callback.answer("❌ Некорректные данные", show_alert=True)
            return

        try:
            # Получить зависимости
            cache = manager.middleware_data.get("cache")
            xui_session: XUISession = manager.middleware_data.get("xui_session")

            if not cache or not xui_session:
                await callback.answer("❌ Сервис недоступен", show_alert=True)
                return

            # Получить ключ из кеша
            key: Optional[Key] = await cache.keys.get(CacheKeyManager.key(email))

            if not key:
                await callback.answer("❌ Ключ не найден", show_alert=True)
                return

            # Получить контейнер и сервис данных
            container = manager.middleware_data.get("container")
            if not container:
                logger.error(
                    "Экземпляр контейнера отсутсвует в мидлвари",
                    user_id=callback.from_user.id if hasattr(callback, "from_user") else None,
                    handler="key_change_date"
                )
                await callback.answer("❌ Контейнер не инициализирован", show_alert=True)
                return

            model_data: ServiceDataModel = container.resolve(ServiceDataModel)
            pool: asyncpg.Pool = container.resolve(asyncpg.Pool)

            # Конвертировать date в datetime с UTC и обновить дату истечения (миллисекунды)
            if not isinstance(selected_date, datetime):
                # Если это date, а не datetime, то конвертировать в datetime
                selected_date = datetime.combine(selected_date, datetime.min.time())
            if selected_date.tzinfo is None:
                selected_date = selected_date.replace(tzinfo=timezone.utc)
            expiry_ms = int(selected_date.timestamp() * 1000)
            key.expiry_time = expiry_ms

            # Обновить в XUI, DB и кеше параллельно
            logger.debug("Обновление даты истечения ключа", email=email, new_date=selected_date)
            results = await asyncio.gather(
                xui_session.extend_client_key(key),
                model_data.keys.update(pool, key, {"email": key.email}),
                cache.keys.set(CacheKeyManager.key(email), key),
                return_exceptions=True,
            )

            errors = [r for r in results if isinstance(r, Exception)]
            if errors:
                logger.error("Ошибки при обновлении даты ключа", email=email, errors=errors)

            # Сбросить флаги уведомлений и трафик через KeyResetter
            resetter: KeyResetter = container.resolve(KeyResetter)
            await resetter.reset_key_after_renewal(pool, key)

            logger.info(
                "Дата истечения ключа обновлена",
                email=email,
                new_date=selected_date.strftime("%d.%m.%Y")
            )
            await callback.answer(
                f"✅ Дата истечения обновлена на {selected_date.strftime('%d.%m.%Y')}",
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
                "Ошибка при обновлении даты ключа",
                email=email,
                error=str(e),
                exc_info=True,
            )
            await callback.answer(
                f"❌ Ошибка при обновлении: {str(e)}", show_alert=True
            )
