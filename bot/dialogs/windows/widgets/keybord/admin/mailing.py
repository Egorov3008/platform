from aiogram_dialog.widgets.kbd import Column, Button, Radio
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.text import Const, Format

from dialogs.windows.base import KeyboardBuilder
from states import AdminMassMailing
from getters.on_click.admin_click import (
    on_click_confirmation_of_sending,
    on_click_change_status,
    on_click_mass_mailing,
)


class MailingInputKeyboard(KeyboardBuilder):
    """Клавиатура ввода сообщения для массовой рассылки."""

    def build(self):
        return (
            TextInput(
                id="text",
                type_factory=str,
                on_success=on_click_confirmation_of_sending,
            ),
            Button(Const("◀️ Отмена"), id="cancel", on_click=lambda c, _b, m: m.done()),
        )  # type: ignore


class MailingConfirmKeyboard(KeyboardBuilder):
    """Клавиатура подтверждения массовой рассылки."""

    def build(self):
        return Column(
            Radio(
                checked_text=Format("✅ {item[0]}"),
                unchecked_text=Format("{item[0]}"),
                id="pin_message",
                item_id_getter=lambda x: str(x[1]),
                items="statuses",
                on_click=on_click_change_status,  # type: ignore
            ),
            Button(Const("🔄 Изменить сообщение"), id="edit", on_click=self._on_edit),
            Button(
                Const("✅ Подтвердить отправку"),
                id="confirm_send",
                on_click=on_click_mass_mailing,
            ),
            Button(Const("◀️ Отмена"), id="cancel", on_click=lambda c, _b, m: m.done()),
        )

    @staticmethod
    async def _on_edit(callback, button, manager):
        await manager.switch_to(AdminMassMailing.receiving_message)
