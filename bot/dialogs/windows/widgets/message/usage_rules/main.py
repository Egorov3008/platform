from aiogram_dialog.widgets.text import Const, Text

from dialogs.windows.base import MessageBuilder


class UsageRulesMainMessage(MessageBuilder):
    def build(self) -> Text:
        return Const(
            "📋 <b>Правила использования VPN</b>\n\n"
            "Добро пожаловать! Здесь вы найдёте основные правила использования нашего сервиса.\n\n"
            "Выберите номер страницы для просмотра подробной информации →"
        )


class UsageRulesPageMessage(MessageBuilder):
    """Base message for all usage rules pages"""

    def build(self) -> Text:
        return Const("Страница правил")
