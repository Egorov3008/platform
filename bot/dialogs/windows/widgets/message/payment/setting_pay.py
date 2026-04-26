from aiogram_dialog.widgets.text import Text, Format, Multi, Case, Const

from dialogs.windows.base import MessageBuilder


class SettingsPayment(MessageBuilder):
    def build(self) -> Text:
        return Multi(
            Format("📦 <b>{tariff_name}</b>\n"),
            Format("⏰ Срок подписки: <b>{number_of_months} месяцев</b>\n"),
            Case(
                {
                    True: Multi(
                        Format("💰 Цена без скидки: <s>{amount_without_volume_discount:.0f} руб.</s>"),
                        Format("🔥 Скидка за объём: <b>{volume_discount_percent}%</b>"),
                    ),
                    False: Const(""),
                },
                selector="has_volume_discount",
            ),
            Case(
                {
                    True: Multi(
                        Format("🎁 Реферальная скидка: <b>-{referral_discount:.0f} руб.</b>"),
                        Format("💳 Итого к оплате: <b>{amount:.0f} руб.</b>\n"),
                    ),
                    False: Format("💳 Итого к оплате: <b>{amount:.0f} руб.</b>\n"),
                },
                selector="has_referral_discount",
            ),
            Const("⚡ Вы можете увеличить срок подписки до 6 месяцев"),
            Const("\n<b>🎁 При оплате от 2 месяцев действует скидка 3 %</b>\n"),
            Const("📊 Используйте кнопки +/- для изменения количества\n"),
            Const("После оплаты ключ будет автоматически активирован 🚀"),
        )
