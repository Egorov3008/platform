from aiogram_dialog.widgets.text import Text, Format

from dialogs.windows.base import MessageBuilder


class CaptchaMessage(MessageBuilder):
    """Сообщение с арифметической капчей."""

    def build(self) -> Text:
        return Format(
            "🔐 <b>Проверка</b>\n\n"
            "Пожалуйста, решите пример:\n\n"
            "🧮 <b>{captcha_question}</b>\n\n"
            "Введите ответ цифрами:"
        )
