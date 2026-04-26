from aiogram_dialog.widgets.text import Format

from dialogs.windows.base import MessageBuilder


class UserMessageBuilder(MessageBuilder):
    def build(self):
        return Format(
            "<b>Личный кабинет</b>\n"
            "<b>Профиль:</b> {username}\n"
            "<b>Количество ключей:</b> {count_key}\n"
            "🚀 <b>+ Новый ключ</b> - приобрести дополнительный ключ\n"
            "<b>📋 Мои ключи</b> - ваши активные подключения\n\n"
            "💎 <b>Тарифы</b> - доступные варианты подписки"
        )
