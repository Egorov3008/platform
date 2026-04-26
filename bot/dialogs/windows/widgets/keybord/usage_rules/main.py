from aiogram_dialog.widgets.kbd import Column, Row, SwitchTo, Cancel, Keyboard
from aiogram_dialog.widgets.text import Const

from dialogs.windows.base import KeyboardBuilder
from states.rulse import UsageRules


class UsageRulesMainKeyboard(KeyboardBuilder):
    def build(self) -> Keyboard:
        return Column(
            Row(
                SwitchTo(Const("1️⃣"), id="page1", state=UsageRules.page1),
                SwitchTo(Const("2️⃣"), id="page2", state=UsageRules.page2),
                SwitchTo(Const("3️⃣"), id="page3", state=UsageRules.page3),
            ),
            Row(
                SwitchTo(Const("4️⃣"), id="page4", state=UsageRules.page4),
                SwitchTo(Const("5️⃣"), id="page5", state=UsageRules.page5),
                SwitchTo(Const("6️⃣"), id="page6", state=UsageRules.page6),
            ),
            Row(
                SwitchTo(Const("7️⃣"), id="page7", state=UsageRules.page7),
                SwitchTo(Const("8️⃣"), id="page8", state=UsageRules.page8),
                SwitchTo(Const("9️⃣"), id="page9", state=UsageRules.page9),
            ),
            Row(Cancel(Const("◀️ Назад"))),
        )


class UsageRulesPageKeyboard(KeyboardBuilder):
    """Navigation keyboard for individual rule pages"""

    def build(self) -> Keyboard:
        return Column(
            Row(
                SwitchTo(Const("⬅️ Назад"), id="back", state=UsageRules.main),
                SwitchTo(Const("Вперед ➡️"), id="next", state=UsageRules.main),
            ),
            Row(Cancel(Const("Выход"))),
        )
