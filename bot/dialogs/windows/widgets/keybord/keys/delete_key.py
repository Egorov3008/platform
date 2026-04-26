import asyncio
from typing import Any, Optional

from asyncpg import Pool
from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, StartMode
from aiogram_dialog.widgets.kbd import Row, Button, Back
from aiogram_dialog.widgets.text import Const

from client import XUISession
from dialogs.windows.base import KeyboardBuilder
from logger import logger
from services.cache.key_manager import CacheKeyManager
from services.core.data.service import ServiceDataModel
from models import Key
from states import MainMenu


class DeleteKeyKeyboard(KeyboardBuilder):
    """Клавиатура окна подтверждения удаления ключа."""

    def __init__(
        self, model_data: ServiceDataModel, xui_session: XUISession, pool: Pool
    ):
        self.key_data = model_data.keys
        self.key_cache = model_data.cache_service.keys
        self.xui = xui_session
        self.pool = pool

    async def _delete_key(
        self,
        callback: CallbackQuery,
        button: Any,
        dialog_manager: DialogManager,
        **kwargs,
    ):
        """Удаление ключа."""
        email = dialog_manager.dialog_data.get("email")

        key: Optional[Key] = await self.key_data.get_data(email)

        if not key:
            await callback.answer("❌ Ключ не найден", show_alert=True)
            return

        try:
            logger.debug("Удаление ключа", email=email)
            results = await asyncio.gather(
                self.xui.delete_client(
                    email=email, inbound_id=key.inbound_id, client_id=key.client_id
                ),
                self._delete_from_db(self.pool, email),
                self.key_cache.delete(CacheKeyManager.key(email)),
                return_exceptions=True,
            )

            errors = [r for r in results if isinstance(r, Exception)]
            if errors:
                logger.error("Ошибки при удалении ключа", email=email, errors=errors)

            await dialog_manager.start(MainMenu.main, mode=StartMode.RESET_STACK)
            await callback.answer(f"Ключ {email} удалён 🆗", show_alert=True)

        except Exception as e:
            logger.error(
                "Ошибка при удалении ключа", email=email, error=str(e), exc_info=True
            )
            await callback.answer(
                f"Ошибка при удалении ключа: {str(e)}", show_alert=True
            )

    async def _delete_from_db(self, session, email: str):
        # Получаем ключ из кэша/БД
        key = await self.key_data.get_data(email)
        if key:
            # Используем правильный метод удаления из BaseData
            await self.key_data.delete_data(session, key)

    def build(self):
        return Row(
            Button(Const("Да"), id="confirm_delete", on_click=self._delete_key),
            Back(Const("Нет")),
        )
