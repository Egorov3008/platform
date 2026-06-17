from aiogram_dialog.widgets.text import Text, Const, Format, Multi, Case

from dialogs.windows.base import MessageBuilder


class KeyDetailsMessage(MessageBuilder):
    """Сообщение окна детального просмотра ключа."""

    def build(self) -> Text:
        return create_key_details_widget()


def create_key_details_widget() -> Text:
    """Создает виджет для отображения деталей ключа"""
    return Multi(
        Case(
            {
                True: Const("❌ Ключ не найден"),
                False: Const("")
            },
            selector="error"
        ),
        Case(
            {
                False: create_key_details_content(),
                True: Const("")
            },
            selector="error"
        )
    )


def create_key_details_content() -> Text:
    """Создает содержимое деталей ключа (когда ошибки нет)"""
    return Multi(
        Const("🔑 <b>Информация о ключе</b>"),
        Format("<code>{keys}</code>"),
        Format("<b>📦 Тариф:</b> {tariff_name}"),
        Format("<b>📊 Трафик:</b>"),
        Format("└ Использовано: {used_traffic:.2f} GB"),
        Format("<b>🕒 Срок действия:</b>"),
        Format("├ Дата: {expiry_date}"),
        Format("├ Статус: {status_emoji} {status_text}"),
        Format("└ {time_left_message}"),
        Case(
            {
                True: Const("🎁 <b>Пробный период</b>\n<i>Это пробная версия тарифа</i>"),
                False: Const("")
            },
            selector="is_trial"
        ),
        Case(
            {
                False: Const("⚠️ <b>Внимание</b>\n<i>Подписка истекла. Пожалуйста, продлите её.</i>"),
                True: Const("")
            },
            selector="is_active"
        )
    )
