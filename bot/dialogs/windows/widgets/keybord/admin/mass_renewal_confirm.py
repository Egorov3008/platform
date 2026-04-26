"""Клавиатура подтверждения массового продления."""

import asyncio
from typing import Any

import asyncpg
from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, StartMode
from aiogram_dialog.widgets.kbd import Button, SwitchTo, Cancel, Column
from aiogram_dialog.widgets.text import Const

from client import XUISession
from dialogs.windows.base import KeyboardBuilder
from logger import logger
from services.cache.service import CacheService
from services.conteiner.app import get_container
from services.core.data.service import ServiceDataModel
from services.core.keys.mass_renewal import MassKeyRenewal
from services.core.keys.utils.reset import KeyResetter
from states import AdminManager, AdminMassRenewal


class AdminMassRenewalConfirmKeyboard(KeyboardBuilder):
    """Клавиатура подтверждения массового продления."""

    def build(self):
        return Column(
            Button(
                Const("✅ Подтвердить продление"),
                id="confirm_mass_renewal",
                on_click=self._on_confirm,
            ),
            SwitchTo(
                Const("🔙 Отмена"),
                id="cancel_mass_renewal",
                state=AdminMassRenewal.select_segment,
            ),
            Cancel(Const("🚪 Выход")),
        )

    @staticmethod
    async def _on_confirm(
        callback: CallbackQuery,
        button: Any,
        manager: DialogManager,
        **kwargs,
    ):
        """Подтвердить массовое продление."""
        try:
            keys_to_renew = manager.dialog_data.get("keys_to_renew", [])
            days = manager.dialog_data.get("renewal_days", 0)

            if not keys_to_renew or not days:
                await callback.answer(
                    "❌ Нет данных для продления",
                    show_alert=True,
                )
                return

            cache: CacheService = manager.middleware_data.get("cache")
            xui_session: XUISession = manager.middleware_data.get("xui_session")
            container = manager.middleware_data.get("container")

            if not cache or not xui_session or not container:
                await callback.answer(
                    "❌ Сервисы недоступны",
                    show_alert=True,
                )
                return

            pool: asyncpg.Pool = container.resolve(asyncpg.Pool)
            resetter: KeyResetter = container.resolve(KeyResetter)

            # Создаём сервис массового продления
            renewal_service = MassKeyRenewal(
                xui_session=xui_session,
                cache=cache,
                resetter=resetter,
            )

            # Отправляем сообщение о начале процесса
            await callback.message.answer(
                f"⏳ Начинаю массовое продление {len(keys_to_renew)} ключей на {days} дней..."
            )

            # Выполняем продление
            report = await renewal_service.renew_keys(
                pool=pool,
                keys=keys_to_renew,
                days=days,
            )

            # Отправляем отчёт
            await callback.message.answer(
                report.format_details(),
                parse_mode="HTML",
            )

            await callback.answer("✅ Массовое продление завершено", show_alert=True)

            # Возвращаемся в админ-панель
            await manager.start(
                AdminManager.main,
                mode=StartMode.RESET_STACK,
            )

        except Exception as e:
            logger.error(
                "Ошибка при массовом продлении",
                error=str(e),
                exc_info=True,
            )
            await callback.answer(
                f"❌ Ошибка: {str(e)}",
                show_alert=True,
            )
