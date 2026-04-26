"""Клавиатура для подтверждения удаления пользователя."""

from typing import Any, Optional

import punq
from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Column, Button, Cancel
from aiogram_dialog.widgets.text import Const

from dialogs.windows.base import KeyboardBuilder
from logger import logger
from services.cache.key_manager import CacheKeyManager
from services.cache.service import CacheService
from services.core.user.utils.delete_data import DeleteUser
from states import AdminManager


class AdminUserDeleteConfirmKeyboard(KeyboardBuilder):
    """Клавиатура подтверждения удаления пользователя."""

    def build(self):
        return Column(
            Button(
                Const("✅ Подтвердить удаление"),
                id="confirm_delete_user",
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
        """Удалить пользователя после подтверждения."""
        tg_id = manager.start_data.get("tg_id")

        if not tg_id:
            await callback.answer("❌ ID пользователя не передан", show_alert=True)
            return

        cache_service: Optional[CacheService] = manager.middleware_data.get("cache")
        if not cache_service:
            await callback.answer(
                "❌ Ошибка: не удалось получить доступ к кешу", show_alert=True
            )
            return

        cache_key = CacheKeyManager.user(tg_id)
        user = await cache_service.users.get(cache_key)

        if not user:
            await callback.answer(
                f"❌ Пользователь {tg_id} не найден в системе", show_alert=True
            )
            return

        container: Optional[punq.Container] = manager.middleware_data.get("container")
        if not container:
            await callback.answer(
                "❌ Ошибка: не удалось получить DI контейнер", show_alert=True
            )
            return

        try:
            delete_service: DeleteUser = container.resolve(DeleteUser)
            await delete_service.delete(tg_id)

            await cache_service.users.delete(cache_key)
            logger.info("Пользователь удалён из системы", tg_id=tg_id)

            await callback.answer(
                f"✅ Пользователь {tg_id} успешно удален из системы", show_alert=True
            )

            await manager.start(AdminManager.main)

        except Exception as e:
            logger.error("Ошибка при удалении пользователя", tg_id=tg_id, error=str(e))
            await callback.answer(
                f"❌ Ошибка при удалении: {str(e)}", show_alert=True
            )
