"""Message builder для окна статистики платежей."""

from aiogram_dialog.widgets.text import Format

from dialogs.windows.base import MessageBuilder


class PaymentStatsMessage(MessageBuilder):
    """Формирует сообщение для окна статистики платежей."""

    def build(self):
        return Format("{PAYMENT_STATS_MSG}")
