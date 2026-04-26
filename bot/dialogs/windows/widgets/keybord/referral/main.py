import asyncpg
from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Button, Column, CopyText, Start
from aiogram_dialog.widgets.text import Const, Format

from dialogs.windows.base import KeyboardBuilder
from logger import logger
from services.core.referral.link_generator import ReferralLinkGenerator
from states import MainMenu


class ReferralMainKeyboard(KeyboardBuilder):
    def __init__(self, link_generator: ReferralLinkGenerator):
        self._link_generator = link_generator

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
        """Генерация новой реферальной ссылки."""
        tg_id = dialog_manager.event.from_user.id
        container = dialog_manager.middleware_data.get("container")
        pool = container.resolve(asyncpg.Pool)

        try:
            link = await self._link_generator.get_or_create(pool, tg_id)
            share_url = self._link_generator.get_share_url(link.token)
            await callback.answer(f"Ссылка создана!", show_alert=True)
            logger.info("Реферальная ссылка создана через UI", tg_id=tg_id, token=link.token)
        except Exception as e:
            logger.error("Ошибка создания реферальной ссылки", error=str(e), tg_id=tg_id)
            await callback.answer("Ошибка при создании ссылки", show_alert=True)
