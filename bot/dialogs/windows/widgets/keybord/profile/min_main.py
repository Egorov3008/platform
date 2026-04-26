from aiogram_dialog.widgets.kbd import Column, Start, SwitchTo
from aiogram_dialog.widgets.text import Const

from dialogs.windows.base import KeyboardBuilder
from states import KeysInit, GiftStates, MainMenu
from states.payment import PaymentState


class MinMainKeyboard(KeyboardBuilder):
    """Клавиатура упрощённого главного меню."""

    def build(self):
        return Column(
            Start(
                Const("🔗 Подключиться"),
                id="trial_min",
                state=KeysInit.create_trial,
                when="trial",
            ),
            Start(
                Const("Подарить ключ другу 🎁 NEW!!!"),
                id="gift_min",
                state=GiftStates.main,
                when="check_usage_link",
            ),
            Start(
                Const("+ Новый ключ"),
                id="create_key_min",
                state=PaymentState.view_tariff,
            ),
            Start(
                Const("📋 Мои ключи"),
                id="list_key_min",
                state=KeysInit.list,
                when="check_key",
            ),
            SwitchTo(
                Const("📊 Расширенный режим"), id="switch_advanced", state=MainMenu.main
            ),
        )
