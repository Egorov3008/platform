from aiogram_dialog.widgets.text import Text, Format

from dialogs.windows.base import MessageBuilder


class WelcomeMessage(MessageBuilder):
    def build(self) -> Text:
        return Format(
            "<b>Добро пожаловать в клуб! 🎉</b>\n\n"
            "Теперь у вас есть доступ к сервису «для своих»!\n\n"
            "<b>Нажмите кнопку для активации — и получите:</b>\n"
            "🌟 7 дней пробного периода\n"
            "🌟 10 Гб трафика в подарок\n"
            "🌟 Инструкцию по настройку\n\n"
            "Пробный период закончится, но это только начало!\n"
            "После него вы легко продолжите по одному из тарифов:\n"
        )
