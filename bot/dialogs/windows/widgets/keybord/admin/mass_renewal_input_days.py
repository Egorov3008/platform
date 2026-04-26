"""Клавиатура ввода количества дней для массового продления."""

from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import Button
from aiogram_dialog.widgets.text import Const

from dialogs.windows.base import KeyboardBuilder
from getters.on_click.admin_keys import on_input_renewal_days


class AdminMassRenewalInputDaysKeyboard(KeyboardBuilder):
    """Клавиатура ввода дней для массового продления."""

    def build(self):
        return (
            TextInput(
                id="input_days",
                type_factory=int,
                on_success=on_input_renewal_days,
            ),
            Button(Const("🔙 Отмена"), id="cancel", on_click=lambda c, _b, m: m.done()),
        )
