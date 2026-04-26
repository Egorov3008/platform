from aiogram_dialog.widgets.kbd import Column, Cancel, Select
from aiogram_dialog.widgets.text import Const, Format
from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager

from dialogs.windows.base import KeyboardBuilder
from states.key import KeysInit


class KeyListKeyboard(KeyboardBuilder):
    """Клавиатура окна списка ключей."""

    async def _on_key_selected(
        self,
        callback: CallbackQuery,
        widget: Select,
        dialog_manager: DialogManager,
        item_id: str,
    ):
        email = dialog_manager.dialog_data.get(item_id)
        dialog_manager.dialog_data["email"] = email
        await dialog_manager.switch_to(KeysInit.key)

    def build(self):
        return Column(
            Select(
                Format("{item[1]}"),
                id="s_keys",
                item_id_getter=lambda x: str(x[0]),
                items="key_data",
                on_click=self._on_key_selected,
            ),
            Cancel(Const("Назад"), id="back_list"),
        )
