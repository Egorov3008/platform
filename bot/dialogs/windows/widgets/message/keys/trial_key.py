from aiogram_dialog.widgets.text import Text, Format

from dialogs.windows.base import MessageBuilder


INSTRUCTIONS_TRIAL = (
    "🎉 <b>Ваш пробный ключ активирован!</b>\n\n"
    "📋 <b>Быстрая инструкция по подключению:</b>\n"
    "1. <b>Скопируйте ключ</b> кнопкой ниже\n"
    "2. <b>Откройте приложение</b> и нажмите +\n"
    "3. <b>Вставьте из буфера обмена</b>\n\n"
    "🔗 Или нажмите <b>«Вставить ключ»</b> — и приложение откроется автоматически.\n\n"
    "💬 Возникли вопросы? Напишите в поддержку!"
)


class TrialKeyMessage(MessageBuilder):
    """Сообщение окна пробного ключа."""

    def build(self) -> Text:
        return Format(INSTRUCTIONS_TRIAL)
