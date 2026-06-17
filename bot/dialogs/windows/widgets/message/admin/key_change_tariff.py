"""Сообщения для изменения тарифа ключа."""

from aiogram_dialog.widgets.text import Format

from dialogs.windows.base import MessageBuilder


class AdminKeyChangeTariffMessage(MessageBuilder):
    """Сообщение для окна выбора тарифа."""

    def build(self):
        """Построить сообщение выбора тарифа."""
        return Format(
            "🔄 <b>Изменение тарифа</b>\n\n"
            "<b>Email ключа:</b> <code>{email}</code>\n\n"
            "Выберите новый тариф из списка ниже:"
        )


class AdminKeyChangeTariffConfirmMessage(MessageBuilder):
    """Сообщение подтверждения изменения тарифа."""

    def build(self):
        """Построить сообщение подтверждения."""
        return Format(
            "✅ <b>Подтверждение изменения тарифа</b>\n\n"
            "<b>Email ключа:</b> <code>{email}</code>\n"
            "<b>Новый тариф:</b> <code>{tariff_name}</code>\n\n"
            "Подтвердите изменение:"
        )
