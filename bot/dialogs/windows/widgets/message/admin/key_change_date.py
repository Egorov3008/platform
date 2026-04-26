"""Сообщения для изменения даты истечения ключа."""

from aiogram_dialog.widgets.text import Format

from dialogs.windows.base import MessageBuilder


class AdminKeyChangeDateMessage(MessageBuilder):
    """Сообщение для окна выбора даты истечения."""

    def build(self):
        """Построить сообщение выбора даты."""
        return Format(
            "📅 <b>Изменение даты истечения</b>\n\n"
            "<b>Email ключа:</b> <code>{email}</code>\n\n"
            "Выберите новую дату истечения в календаре ниже:"
        )


class AdminKeyChangeDateConfirmMessage(MessageBuilder):
    """Сообщение подтверждения изменения даты истечения."""

    def build(self):
        """Построить сообщение подтверждения."""
        return Format(
            "✅ <b>Подтверждение изменения даты</b>\n\n"
            "<b>Email ключа:</b> <code>{email}</code>\n"
            "<b>Новая дата истечения:</b> <code>{selected_date_formatted}</code>\n\n"
            "Подтвердите изменение:"
        )
