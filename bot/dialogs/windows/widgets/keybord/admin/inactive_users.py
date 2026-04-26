"""Клавиатуры для модуля очистки неактивных пользователей."""

from typing import Any, Optional

import asyncpg
import punq
from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Column, Button, SwitchTo, Cancel, Start
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog import StartMode

from dialogs.windows.base import KeyboardBuilder
from logger import logger
from models import User
from services.cache.service import CacheService
from services.core.data.service import ServiceDataModel
from states import AdminManager, AdminUserCleanupSG


class InactiveUsersReviewKeyboard(KeyboardBuilder):
    """Клавиатура обзора неактивных пользователей."""

    def build(self):
        return Column(
            Start(
                Const("🗑️ Удалить неактивных"),
                id="delete_inactive",
                state=AdminUserCleanupSG.confirm,
            ),
            Start(Const("🔙 Назад"), id="back_main", state=AdminManager.main, mode=StartMode.RESET_STACK),
        )


class InactiveUsersConfirmKeyboard(KeyboardBuilder):
    """Клавиатура подтверждения удаления неактивных пользователей."""

    def build(self):
        return Column(
            Button(
                Const("✅ Подтвердить удаление"),
                id="confirm_delete_inactive",
                on_click=self._on_confirm,
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
        """Удалить всех неактивных пользователей после подтверждения."""
        inactive_users: list = manager.dialog_data.get("inactive_users", [])

        if not inactive_users:
            await callback.answer(
                "❌ Нет пользователей для удаления", show_alert=True
            )
            return

        count = len(inactive_users)

        cache_service: Optional[CacheService] = manager.middleware_data.get("cache")
        if not cache_service:
            await callback.answer(
                "❌ Ошибка: не удалось получить доступ к кешу", show_alert=True
            )
            return

        container: Optional[punq.Container] = manager.middleware_data.get("container")
        if not container:
            await callback.answer(
                "❌ Ошибка: не удалось получить DI контейнер", show_alert=True
            )
            return

        try:
            model_data: ServiceDataModel = container.resolve(ServiceDataModel)
            pool: asyncpg.Pool = container.resolve(asyncpg.Pool)
            
            if not pool:
                await callback.answer(
                    "❌ Ошибка: не удалось получить подключение к базе данных", show_alert=True
                )
                return

            deleted_count = 0
            for user in inactive_users:
                if isinstance(user, User):
                    await model_data.users.delete_data(pool, user)
                    # Очищаем кеш
                    from services.cache.key_manager import CacheKeyManager
                    cache_key = CacheKeyManager.user(user.tg_id)
                    await cache_service.users.delete(cache_key)
                    deleted_count += 1

            logger.info(
                "Удалены неактивные пользователи",
                count=deleted_count,
            )

            await callback.answer(
                f"✅ Удалено {deleted_count} неактивных пользователей",
                show_alert=True,
            )

            await manager.start(AdminManager.main)

        except Exception as e:
            logger.error(
                "Ошибка при удалении неактивных пользователей",
                error=str(e),
                exc_info=True,
            )
            await callback.answer(
                f"❌ Ошибка при удалении: {str(e)}", show_alert=True
            )
