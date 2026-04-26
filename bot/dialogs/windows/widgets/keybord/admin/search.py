from aiogram.types import Message
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Column, SwitchTo, Back, Cancel
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.text import Const

from dialogs.windows.base import KeyboardBuilder
from states import AdminSearchManagementSG
from getters.on_click.user_managment import on_click_search_tg_id, on_click_search_email


async def error_tg_id(message: Message, _dialog, manager: DialogManager, _error):
    """Обработчик ошибки для ввода tg_id."""
    await message.answer("ID Должен быть числом!")


async def error_email(message: Message, _dialog, manager: DialogManager, _error):
    """Обработчик ошибки для ввода email."""
    await message.answer("EMAIL должен быть строкой!")


class SearchMainKeyboard(KeyboardBuilder):
    """Клавиатура главного меню поиска."""

    def build(self):
        return Column(
            SwitchTo(
                Const("Поиск пользователя по id 🆔"),
                id="search_for_tg_id",
                state=AdminSearchManagementSG.search_tg_id,
            ),
            SwitchTo(
                Const("Поиск ключа по email 📨"),
                id="search_email",
                state=AdminSearchManagementSG.search_email,
            ),
            Cancel(Const("🔙 Назад")),
        )


class SearchTgIdKeyboard(KeyboardBuilder):
    """Клавиатура поиска по tg_id."""

    def build(self):
        return (
            TextInput(
                id="tg_id",
                type_factory=int,
                on_success=on_click_search_tg_id,
                on_error=error_tg_id,
            ),
            Back(Const("🔙 Назад")),
        )  # type: ignore


class SearchEmailKeyboard(KeyboardBuilder):
    """Клавиатура поиска по email."""

    def build(self):
        return (
            TextInput(
                id="email",
                type_factory=str,
                on_success=on_click_search_email,
                on_error=error_email,
            ),
            Back(Const("🔙 Назад")),
        )  # type: ignore
