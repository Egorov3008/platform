from aiogram_dialog.widgets.text import Text, Format

from dialogs.windows.base import MessageBuilder


class MinMainMessage(MessageBuilder):
    """Сообщение упрощённого главного меню."""

    def build(self) -> Text:
        return Format(
            "<b>Личный кабинет</b>\n\n"
            "<b>Профиль:</b> {username}\n"
            "<b>Количество ключей:</b> {count_key}"
        )
