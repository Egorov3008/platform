"""Сообщения для модуля очистки неактивных пользователей."""

from aiogram_dialog.widgets.text import Format

from dialogs.windows.base import MessageBuilder


class InactiveUsersReviewMessage(MessageBuilder):
    """Сообщение с результатами поиска неактивных пользователей."""

    def build(self):
        return Format(
            "🧹 <b>Поиск неактивных пользователей</b>\n\n"
            "Найдено пользователей, которые заблокировали бота и не имеют ключей:\n"
            "👤 <b>{inactive_users_count}</b>\n\n"
            "Нажмите «Удалить неактивных» для очистки."
        )


class InactiveUsersConfirmMessage(MessageBuilder):
    """Сообщение подтверждения удаления неактивных пользователей."""

    def build(self):
        return Format(
            "🔴 <b>Подтверждение удаления</b>\n\n"
            "Вы действительно хотите удалить <b>{inactive_users_count}</b> неактивных пользователей?\n\n"
            "⚠️ <b>Действие необратимо!</b>"
        )
