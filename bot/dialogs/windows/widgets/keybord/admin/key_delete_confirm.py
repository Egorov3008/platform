"""Клавиатура для подтверждения удаления ключа."""

import asyncio
from typing import Any, Optional

import asyncpg
from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, StartMode
from aiogram_dialog.widgets.kbd import Column, Button, Cancel

from aiogram_dialog.widgets.text import Const

from dialogs.windows.base import KeyboardBuilder
from logger import logger
from services.cache.key_manager import CacheKeyManager
from services.core.data.service import ServiceDataModel
from services.conteiner.app import get_container
from client import XUISession
from models import Key
from states import AdminManager


class AdminKeyDeleteConfirmKeyboard(KeyboardBuilder):
    """Клавиатура подтверждения удаления ключа."""

    def build(self):
        return Column(
            Button(
                Const("✅ Подтвердить удаление"),
                id="confirm_delete",
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
        """Удалить ключ."""
        email = manager.start_data.get("email")

        if not email:
            await callback.answer("❌ Email ключа не передан", show_alert=True)
            return

        try:
            # Получить зависимости из middleware и контейнера
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
            container = await get_container()
            model_data: ServiceDataModel = container.resolve(ServiceDataModel)
            pool: asyncpg.Pool = container.resolve(asyncpg.Pool)

            # Удалить из XUI, DB и кеша параллельно
            logger.debug("Удаление ключа администратором", email=email)
            results = await asyncio.gather(
                xui_session.delete_client(
                    email=email,
                    inbound_id=key.inbound_id,
                    client_id=key.client_id,
                ),
                model_data.keys.delete_data(pool, key),
                cache.keys.delete(CacheKeyManager.key(email)),
                return_exceptions=True,
            )

            errors = [r for r in results if isinstance(r, Exception)]
            if errors:
                logger.error("Ошибки при удалении ключа администратором", email=email, errors=errors)

            logger.info("Ключ удалён администратором", email=email)
            await callback.answer(f"✅ Ключ {email} успешно удалён", show_alert=True)

            # Вернуться в список ключей
            await manager.start(AdminManager.key_list, mode=StartMode.RESET_STACK)

        except Exception as e:
            logger.error(
                "Ошибка при удалении ключа администратором",
                email=email,
                error=str(e),
                exc_info=True,
            )
            await callback.answer(
                f"❌ Ошибка при удалении: {str(e)}", show_alert=True
            )
