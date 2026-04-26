from aiogram_dialog.widgets.text import Text, Const

from dialogs.windows.base import MessageBuilder


class GiftMainMessage(MessageBuilder):
    def build(self) -> Text:
        return Const(
            "🎁 <b>Подарите VIP-доступ другу!</b>\n\n"
            "Отправьте ему эту ссылку — и он получит <b>тариф «160»</b> на целый месяц\n"
            "🔋 <i>1 устройство, 100 ГБ трафика, максимальная скорость!</i>\n\n"
            "✅ Подарок активируется автоматически при регистрации\n"
            "⏰ Действует только для нового пользователя\n\n"
            "👇 Нажмите, чтобы скопировать ссылку и отправить другу:"
        )
