from aiogram_dialog.widgets.kbd import Column, Row, SwitchTo, Keyboard
from aiogram_dialog.widgets.text import Const

from dialogs.windows.base import KeyboardBuilder
from states.instruction import Instruction


class InstructionChoosingKeyboard(KeyboardBuilder):
    def build(self) -> Keyboard:
        return Column(
            Row(
                SwitchTo(Const("ANDROID 🤖"), id="android", state=Instruction.android),
                SwitchTo(Const("IPhone 🍎"), id="iphone", state=Instruction.iphone),
            ),
            Row(
                SwitchTo(Const("Windows 🪟"), id="windows", state=Instruction.windows),
                SwitchTo(Const("Linux 🐧"), id="linux", state=Instruction.linux),
            ),
        )
