"""Сообщения для окон массового продления админ-панели."""

from aiogram_dialog.widgets.text import Const, Format

from dialogs.windows.base import MessageBuilder


class AdminMassRenewalSegmentMessage(MessageBuilder):
    """Сообщение для выбора сегмента массового продления."""

    def build(self):
        return Const(
            "📦 <b>Массовое продление ключей</b>\n\n"
            "Выберите сегмент ключей для продления:\n"
            "• ⏰ Истекают в 24 часа\n"
            "• 📅 Истекают в 7 дней\n"
            "• 📆 Истекают в 30 дней\n"
            "• 🔴 Истёкшие ключи\n"
            "• ✅ Активные ключи\n"
            "• 🔹 Все активные ключи\n\n"
            "После выбора сегмента вам будет предложено ввести количество дней для продления."
        )


class AdminMassRenewalInputDaysMessage(MessageBuilder):
    """Сообщение для ввода количества дней продления."""

    def build(self):
        return Const(
            "📅 <b>Введите количество дней</b>\n\n"
            "На сколько дней нужно продлить выбранные ключи?\n\n"
            "Введите число (например: 30, 60, 90):"
        )


class AdminMassRenewalPreviewMessage(MessageBuilder):
    """Сообщение превью массового продления."""

    def build(self):
        return Format("{preview_message}")
