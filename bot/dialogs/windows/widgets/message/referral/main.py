from aiogram_dialog.widgets.text import Text, Const, Format, Case

from dialogs.windows.base import MessageBuilder


class ReferralMainMessage(MessageBuilder):
    def build(self) -> Text:
        return Case(
            texts={
                True: Format(
                    "👥 <b>Реферальная программа</b>\n\n"
                    "Приглашай друзей и получай бонусы!\n\n"
                    "🔗 <b>Твоя ссылка:</b>\n"
                    "<code>{share_url}</code>\n\n"
                    "📊 <b>Статистика:</b>\n"
                    "Приглашено: {referral_count} чел.\n"
                    "Бонусов получено: {rewards_count}\n"
                    "Сумма бонусов: {rewards_total:.2f} ₽\n"
                    "Доступный баланс: {available_balance:.2f} ₽\n\n"
                    "💡 При первой оплате приглашённого друга "
                    "ты получишь скидку 10% от суммы его платежа!"
                ),
                False: Const(
                    "👥 <b>Реферальная программа</b>\n\n"
                    "Приглашай друзей и получай бонусы!\n\n"
                    "Нажми кнопку ниже, чтобы создать свою реферальную ссылку.\n\n"
                    "💡 При первой оплате приглашённого друга "
                    "ты получишь скидку 10% от суммы его платежа!"
                ),
            },
            selector="has_link",
        )
