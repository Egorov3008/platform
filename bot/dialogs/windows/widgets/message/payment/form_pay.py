from aiogram_dialog.widgets.text import Const, Text

from dialogs.windows.base import MessageBuilder


class InstructionsPaymentMessage(MessageBuilder):
    def build(self) -> Text:
        return Const(
            "💳 <b>Как оплатить тариф:</b>\n\n"
            "1. Нажмите кнопку <b>«Перейти к оплате»</b> 💰\n"
            "2. Оплатите тариф через платежный терминал\n\n"
            "✅ <i>После успешной оплаты вы получите автоматическое уведомление</i>\n\n"
            "🔍 <b>Не пришло уведомление?</b>\n"
            "Вы всегда можете проверить статус:\n\n"
            "1. Нажмите <b>«Проверить статус оплаты»</b> 🔄\n"
            "2. Убедитесь, что платеж прошел\n\n"
            "<i>Если возникнут вопросы — мы на связи!</i> 🤝"
        )
