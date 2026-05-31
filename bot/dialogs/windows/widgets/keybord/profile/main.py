from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, StartMode
from aiogram_dialog.widgets.kbd import Start, Row, Url, Button
from aiogram_dialog.widgets.text import Const
from config import SUPPORT_CHAT_URL
from dialogs.windows.base import KeyboardBuilder

from services.scenarios.create_first_key_scenario import CreateFerstKeyScenario
from states import KeysInit, GiftStates, UsageRules, AdminManager, ReferralSistem
from states.instruction import Instruction
from states.payment import PaymentState
from states.tariff import Tariff


class UserKeyboardBuilder(KeyboardBuilder):
    def __init__(
        self, create_trial_key: CreateFerstKeyScenario
    ):
        self.create_trial_key = create_trial_key

    def build(self):
        return (
            Button(
                Const("🔗 Подключиться к сервису"),
                id="create_trial_key",
                when="trial",
                on_click=self._clicked_create_trial_key,
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
            Row(
                Start(
                    Const("Подарить ключ другу 🎁"),
                    id="partner_program",
                    when="check_usage_link",
                    state=GiftStates.main,
                ),
                Start(
                    Const("👥 Реферальная программа"),
                    id="referral_program",
                    state=ReferralSistem.main,
                ),
            ),
            Row(
                Start(Const("💡 Тарифы"), id="tariff", state=Tariff.preview),
                Button(
                    Const("Правила использования 📃"),
                    id="rules_pdf",
                    on_click=self._clicked_rules_pdf,
                ),
            ),
            Row(
                Url(Const("💬 Поддержка"), url=Const(SUPPORT_CHAT_URL)),
                Start(
                    Const("🔧 Администратор"),
                    id="admin",
                    when="is_admin",
                    state=AdminManager.main,
                ),
            ),
        )

    async def _clicked_create_trial_key(
        self,
        callback: CallbackQuery,
        widget: Button,
        dialog_manager: DialogManager,
        **kwargs,
    ):
        await dialog_manager.start(
            Instruction.choosing_device, mode=StartMode.RESET_STACK
        )

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
        base_dir = Path(__file__).resolve().parent.parent.parent.parent.parent.parent
        pdf_path = base_dir / "Правила использования VPN — Бот только для своих.pdf"

        if pdf_path.exists():
            pdf_file = FSInputFile(pdf_path)
            await callback.message.answer_document(
                document=pdf_file,
                caption="📄 <b>Правила использования VPN</b>\n\nПубличная оферта на предоставление услуг доступа к сервису «Бот только для своих»"
            )
        else:
            await callback.answer("❌ Файл не найден", show_alert=True)
