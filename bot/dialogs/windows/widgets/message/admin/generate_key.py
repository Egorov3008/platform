"""MessageBuilder для админ-диалога генерации ключа."""

from aiogram_dialog.widgets.text import Const, Format

from dialogs.windows.base import MessageBuilder


class GenKeyInputTgIdMessage(MessageBuilder):
    """Сообщение для ввода tg_id."""

    def build(self):
        return Const(
            "<b>🔑 Генерация ключа</b>\n\n"
            "Введите <b>tg_id</b> пользователя:"
        )


class GenKeyChooseTariffMessage(MessageBuilder):
    """Сообщение для выбора тарифа."""

    def build(self):
        return Format(
            "<b>🔑 Генерация ключа</b>\n\n"
            "🆔 ID: <code>{tg_id}</code>\n"
            "Статус: {user_status}\n\n"
            "<b>Выберите тариф:</b>"
        )


class GenKeyConfirmMessage(MessageBuilder):
    """Сообщение подтверждения генерации."""

    def build(self):
        return Format(
            "<b>🔑 Подтверждение генерации ключа</b>\n\n"
            "🆔 ID: <code>{tg_id}</code>\n"
            "💰 Тариф: {tariff_name}\n\n"
            "Подтвердите генерацию ключа."
        )


class GenKeyResultMessage(MessageBuilder):
    """Сообщение с результатом генерации."""

    def build(self):
        return Format(
            "<b>✅ Ключ успешно создан!</b>\n\n"
            "📧 Email: <code>{email}</code>\n"
            "🔗 Ссылка: <code>{link_to_connect}</code>\n"
            "📅 Дней: {days}"
        )