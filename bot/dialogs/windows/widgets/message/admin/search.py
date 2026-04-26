from aiogram_dialog.widgets.text import Const

from dialogs.windows.base import MessageBuilder


class SearchMainMessage(MessageBuilder):
    """Сообщение выбора метода поиска."""

    def build(self):
        return Const("Выберете метод поиска 📌")


class SearchTgIdMessage(MessageBuilder):
    """Сообщение ввода tg_id для поиска."""

    def build(self):
        return Const("Введите tg_id:")


class SearchEmailMessage(MessageBuilder):
    """Сообщение ввода email для поиска ключа."""

    def build(self):
        return Const("Введите email")
