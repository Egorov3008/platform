"""Сообщения для удаления ключа."""

from aiogram_dialog.widgets.text import Format

from dialogs.windows.base import MessageBuilder


class AdminKeyDeleteConfirmMessage(MessageBuilder):
    """Сообщение подтверждения удаления ключа."""

    def build(self):
        """Построить сообщение подтверждения."""
        return Format(
            "🔴 <b>Удаление ключа</b>\n\n"
            "Вы действительно хотите удалить ключ?\n\n"
            "<b>Email:</b> <code>{email}</code>\n"
            "<b>Пользователь:</b> <code>{tg_id}</code>\n\n"
            "⚠️ <b>Действие необратимо!</b>"
        )
