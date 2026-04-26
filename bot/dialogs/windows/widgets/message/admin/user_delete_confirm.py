"""Сообщение подтверждения удаления пользователя."""

from aiogram_dialog.widgets.text import Format

from dialogs.windows.base import MessageBuilder


class AdminUserDeleteConfirmMessage(MessageBuilder):
    """Сообщение подтверждения удаления пользователя."""

    def build(self):
        """Построить сообщение подтверждения."""
        return Format(
            "🔴 <b>Удаление пользователя</b>\n\n"
            "Вы действительно хотите удалить пользователя?\n\n"
            "<b>Telegram ID:</b> <code>{tg_id}</code>\n"
            "<b>Имя:</b> <code>{username}</code>\n"
            "<b>Количество ключей:</b> {keys_count}\n\n"
            "⚠️ <b>Действие необратимо!</b>"
        )
