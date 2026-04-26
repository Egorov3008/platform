from typing import Dict, Any, List

from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import SUPPORT_CHAT_URL
from models.tariffs.tariff import Tariff


class KeyboardBuilder:
    """Построитель клавиатур для различных воронок"""

    def build_key_expiry_keyboard(
        self, email: str, funnel_type: str
    ) -> InlineKeyboardBuilder:
        """Клавиатура для истечения ключа"""
        keyboard = InlineKeyboardBuilder()
        keyboard.row(
            InlineKeyboardButton(
                text="🔄 Продлить ключ",
                callback_data=f"renew_key|{email}|{funnel_type}",
            )
        )
        keyboard.row(
            InlineKeyboardButton(text="👤 Личный кабинет", callback_data="profile")
        )
        return keyboard

    def build_trial_keyboard(self) -> InlineKeyboardBuilder:
        """Клавиатура для активации триала"""
        keyboard = InlineKeyboardBuilder()

        keyboard.row(
            InlineKeyboardButton(
                text="🎁 Активировать пробный период", callback_data="connect_vpn"
            )
        )

        keyboard.row(
            InlineKeyboardButton(
                text="📊 Посмотреть тарифы", callback_data="view_tariffs"
            )
        )

        keyboard.row(
            InlineKeyboardButton(text="💬 Задать вопрос", url=SUPPORT_CHAT_URL)
        )

        keyboard.row(
            InlineKeyboardButton(text="👤 Личный кабинет", callback_data="profile")
        )

        return keyboard

    def build_referral_keyboard(self) -> InlineKeyboardBuilder:
        """Клавиатура для реферальной программы"""
        keyboard = InlineKeyboardBuilder()
        keyboard.row(
            InlineKeyboardButton(
                text="🎁 Получить бонус", callback_data="claim_referral_bonus"
            )
        )
        keyboard.row(
            InlineKeyboardButton(text="📊 Мои рефералы", callback_data="my_referrals")
        )
        return keyboard

    def build_upsell_keyboard(
        self, user_data: Dict[str, Any], premium_tariffs: List[Tariff]
    ) -> InlineKeyboardBuilder:
        """Клавиатура для апсела"""
        keyboard = InlineKeyboardBuilder()

        # Кнопки для каждого премиум тарифа
        for i, tariff in enumerate(premium_tariffs[:3], 1):
            keyboard.row(
                InlineKeyboardButton(
                    text=f"🚀 {tariff.name_tariff} - {tariff.amount}₽",
                    callback_data=f"upgrade_to|{tariff.id}",
                )
            )

        # Дополнительные кнопки
        keyboard.row(
            InlineKeyboardButton(
                text="📊 Сравнить тарифы", callback_data="compare_tariffs"
            )
        )
        keyboard.row(InlineKeyboardButton(text="💬 Консультация", url=SUPPORT_CHAT_URL))
        keyboard.row(
            InlineKeyboardButton(text="👤 Личный кабинет", callback_data="profile")
        )

        return keyboard

    def build_winback_keyboard(self) -> InlineKeyboardBuilder:
        """Клавиатура для возврата пользователей"""
        keyboard = InlineKeyboardBuilder()
        keyboard.row(
            InlineKeyboardButton(
                text="🎁 Получить предложение", callback_data="winback_offer"
            )
        )
        keyboard.row(
            InlineKeyboardButton(
                text="🔄 Восстановить доступ", callback_data="recover_access"
            )
        )
        keyboard.row(
            InlineKeyboardButton(text="💬 Техподдержка", callback_data="support")
        )
        return keyboard

    def build_cross_sell_keyboard(self) -> InlineKeyboardBuilder:
        """Клавиатура для кроссела"""
        keyboard = InlineKeyboardBuilder()
        keyboard.row(
            InlineKeyboardButton(
                text="🔒 Премиум поддержка", callback_data="premium_support"
            )
        )
        keyboard.row(
            InlineKeyboardButton(
                text="🌍 Дополнительные серверы", callback_data="extra_servers"
            )
        )
        keyboard.row(
            InlineKeyboardButton(
                text="📊 Расширенная статистика", callback_data="advanced_stats"
            )
        )
        keyboard.row(
            InlineKeyboardButton(
                text="💬 Узнать подробности", callback_data="more_details"
            )
        )
        return keyboard

    def build_simple_keyboard(
        self,
        main_text: str,
        main_data: str,
        secondary_text: str = "👤 Личный кабинет",
        secondary_data: str = "profile",
    ) -> InlineKeyboardBuilder:
        """Универсальная простая клавиатура"""
        keyboard = InlineKeyboardBuilder()
        keyboard.row(InlineKeyboardButton(text=main_text, callback_data=main_data))
        keyboard.row(
            InlineKeyboardButton(text=secondary_text, callback_data=secondary_data)
        )
        return keyboard

    def build_payment_keyboard(
        self, payment_type: str, item_id: int, amount: float
    ) -> InlineKeyboardBuilder:
        """Клавиатура для оплаты"""
        keyboard = InlineKeyboardBuilder()
        keyboard.row(
            InlineKeyboardButton(
                text=f"💳 Оплатить {amount}₽",
                callback_data=f"payment|{payment_type}|{item_id}",
            )
        )
        keyboard.row(
            InlineKeyboardButton(text="📋 Мои платежи", callback_data="my_payments")
        )
        keyboard.row(
            InlineKeyboardButton(text="👤 Личный кабинет", callback_data="profile")
        )
        return keyboard
