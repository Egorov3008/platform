from aiogram_dialog.widgets.text import Const, Text

from dialogs.windows.base import MessageBuilder


class InstructionsPaymentMessage(MessageBuilder):
    def build(self) -> Text:
        return Const(
            "💳 <b>Как оплатить тариф:</b>\n\n"
            "1. Нажмите кнопку <b>«Перейти к оплате»</b> 💰\n"
            "2. Оплатите тариф через платежный терминал\n\n"
            "✅ <i>После успешной оплаты ключ активируется автоматически — "
            "придёт уведомление в течение нескольких минут.</i>\n\n"
            "💬 <i>Если уведомление не пришло или возникли вопросы — "
            "мы на связи в поддержке!</i>"
        )
