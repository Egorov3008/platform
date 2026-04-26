from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, StartMode
from aiogram_dialog.widgets.kbd import Keyboard, Button
from aiogram_dialog.widgets.text import Const

from dialogs.windows.base import KeyboardBuilder
from states.instruction import Instruction


class WelcomeKeyboard(KeyboardBuilder):
    """Клавиатура для приветственного окна."""

    def build(self) -> Keyboard:
        return Button(
            Const("🎁 Активировать пробный период"),
            id="choosing_device",
            on_click=self._start_instruction,
        )

    async def _start_instruction(
        self, callback: CallbackQuery, button: Button, dialog_manager: DialogManager
    ):
        await dialog_manager.start(
            Instruction.choosing_device, mode=StartMode.RESET_STACK
        )
