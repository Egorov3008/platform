from typing import Optional, List, Dict, Any

from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Start, SwitchTo, Row, Column, Url, Button
from aiogram_dialog.widgets.text import Const, Format

from config import SUPPORT_CHAT_URL
from getters.base import BaseService
from models import User, Key
from services.core.data.service import ServiceDataModel
from services.core.gift.repositories.checker import CheckerGiftLink
from services.core.user.utils.checked_admin import CheckedUser
from states import KeysInit, GiftStates, UsageRules, AdminManager
from states.tariff import Tariff
from states.payment import PaymentState


class MainMenuGetter(BaseService):
    """Класс главного меню."""

    def __init__(
        self,
        model_data: ServiceDataModel,
        checker_link: CheckerGiftLink,
        checked_user: CheckedUser,
        target_state: str = "MainMenu:main",
    ):
        super().__init__(target_state)
        self.user_data = model_data.users
        self.key_data = model_data.keys
        self.checker_link = checker_link
        self.check_user = checked_user
        self.state = "main"

    async def designer_getters(
        self, dialog_manager: DialogManager, **kwargs
    ) -> Dict[str, Any]:
        """Получение данных пользователя."""
        tg_id = dialog_manager.event.from_user.id
        user: Optional[User] = await self.user_data.get_data(tg_id)
        trial: bool = user.trial == 0
        keys: List[Key] = await self.key_data.get_by(tg_id=tg_id)
        count_key = len(keys)
        is_admin = self.check_user.check(tg_id)
        check_key = count_key > 0
        check_usage_link = await self.checker_link.check(tg_id)

        return {
            "username": user.username or tg_id,
            "count_key": count_key,
            "trial": trial,
            "is_admin": is_admin,
            "check_key": check_key,
            "check_usage_link": check_usage_link,
        }

    def designer_msg(self) -> Format:
        """Дизайн сообщения."""
        return Format(
            "<b>Личный кабинет</b>\n"
            "👤 <b>{username}</b>\n"
            "🔑 <b>Ключей:</b> {count_key}\n\n"
            "🚀 + Новый ключ\n"
            "📋 Мои ключи\n"
            "💎 Тарифы\n"
            "🎥 Инструкция\n"
            "⚡ Упрощённый режим"
        )

    def designer_keyboard(self):
        """Дизайн клавиатуры."""
        return [
            Column(
                Start(
                    Const("🔗 Подключиться к сервису"),
                    id="create_trial_key",
                    when="trial",
                    state=KeysInit.create_trial,
                )
            ),
            Row(
                Start(
                    Const("+ Новый ключ"),
                    id="create_key",
                    state=PaymentState.view_tariff,
                ),
                Start(
                    Const("📋 Мои ключи"),
                    id="list_key",
                    when="check_key",
                    state=KeysInit.list,
                ),
            ),
            Column(
                Start(
                    Const("Подарить ключ другу 🎁 NEW!!!"),
                    id="partner_program",
                    when="check_usage_link",
                    state=GiftStates.main,
                ),
                SwitchTo(Const("💡 Тарифы"), id="tariff", state=Tariff.preview),
                Button(
                    Const("Правила использования 📃"),
                    id="rules_pdf",
                    on_click=self._clicked_rules_pdf,
                ),
                Url(Const("💬 Поддержка"), url=Const(SUPPORT_CHAT_URL)),
                Start(
                    Const(text="🔧 Администратор"),
                    id="admin",
                    when="is_admin",
                    state=AdminManager.main,
                ),
            ),
        ]

    async def _clicked_rules_pdf(
        self,
        callback: CallbackQuery,
        widget: Button,
        dialog_manager: DialogManager,
        **kwargs,
    ):
        """Отправляет PDF файл с правилами использования."""
        from pathlib import Path
        from aiogram.types import FSInputFile

        # Путь к файлу относительно корня проекта
        base_dir = Path(__file__).resolve().parent.parent.parent
        pdf_path = base_dir / "Правила использования VPN — Бот только для своих.pdf"

        if pdf_path.exists():
            pdf_file = FSInputFile(pdf_path)
            await callback.message.answer_document(
                document=pdf_file,
                caption="📄 <b>Правила использования VPN</b>\n\nПубличная оферта на предоставление услуг доступа к сервису «Бот только для своих»"
            )
        else:
            await callback.answer("❌ Файл не найден", show_alert=True)
