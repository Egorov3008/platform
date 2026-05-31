from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Button, Column, CopyText, Start
from aiogram_dialog.widgets.text import Const, Format

from api.backend_client import BackendAPIClient
from config import BOT_NAME
from dialogs.windows.base import KeyboardBuilder
from logger import logger
from states import MainMenu


class ReferralMainKeyboard(KeyboardBuilder):
    def __init__(self, backend_client: BackendAPIClient):
        self._backend = backend_client

    def build(self):
        return Column(
            CopyText(
                Const("📋 Скопировать ссылку"),
                copy_text=Format("{share_url}"),
                when="has_link",
            ),
            Button(
                Const("🔗 Создать реферальную ссылку"),
                id="generate_referral_link",
                when="no_link",
                on_click=self._on_generate_link,
            ),
            Start(Const("👤 В личный кабинет"), id="profile", state=MainMenu.main),
        )

    async def _on_generate_link(
        self,
        callback: CallbackQuery,
        widget: Button,
        dialog_manager: DialogManager,
        **kwargs,
    ):
        """Генерация новой реферальной ссылки через backend API."""
        tg_id = dialog_manager.event.from_user.id
        try:
            link = await self._backend.admin_create_referral_link(tg_id)
            if not link:
                raise RuntimeError("Backend returned empty link")
            token = link.get("token")
            share_url = f"https://t.me/{BOT_NAME}?start={token}"
            await callback.answer("Ссылка создана!", show_alert=True)
            logger.info("Реферальная ссылка создана через backend", tg_id=tg_id, token=token)
        except Exception as e:
            logger.error("Ошибка создания реферальной ссылки", error=str(e), tg_id=tg_id)
            await callback.answer("Ошибка при создании ссылки", show_alert=True)
