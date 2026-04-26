from typing import Dict, Any, List, Optional

from models.tariffs.tariff import Tariff


class MessageBuilder:
    """Построитель сообщений для различных воронок"""

    def build_key_expiry_message(self, key_data: Any, hours_left: int) -> str:
        """Сообщение об истечении ключа"""
        from datetime import datetime

        expiry_date = datetime.fromtimestamp(key_data.expiry_time / 1000)

        return (
            f"⚠️ Ваш ключ {key_data.email} истекает через {hours_left} часов!\n"
            f"⏳ Дата окончания: {expiry_date:%Y-%m-%d %H:%M}\n"
            f"Для продления ключа требуется {key_data.amount} руб."
        )

    def build_trial_reminder_message(
        self, discount: float = 0, tariffs: List[Tariff] = None
    ) -> str:
        """Построение сообщения напоминания о триале"""
        if not tariffs:
            tariffs = []

        message = "🎁 <b>Специальное предложение для новых пользователей!</b>\n\n"

        if discount > 0:
            message += f"🔥 <b>Ваша эксклюзивная скидка {discount}%!</b>\n\n"

        # Показываем не более 3 тарифов
        for tariff in tariffs[:3]:
            original_price = tariff.amount
            discounted_price = original_price - (original_price * (discount / 100))

            message += (
                f'🏷️ Тариф "{tariff.name_tariff}"\n'
                f"   💰 <s>{original_price}₽</s> → <b>{discounted_price:.0f}₽</b>\n"
                f"   📦 {tariff.description}\n"
                f"   🔥 Экономия: {original_price - discounted_price:.0f}₽\n"
                f"────────────────────\n"
            )

        message += (
            "\n🎯 <b>Что вы получите:</b>\n"
            "• 🆓 <b>7 дней бесплатного использования</b>\n"
            "• 📊 <b>10 ГБ трафика</b>\n"
            "• 🌍 <b>Доступ ко всем серверам</b>\n"
            "• ⚡ <b>Высокая скорость</b>\n\n"
            "🎯 <b>Как активировать:</b>\n"
            '1. Нажмите кнопку "Активировать пробный период"\n'
            "2. Выберите удобный сервер\n"
            "3. Начните пользоваться сразу!\n\n"
            "⏳ <b>Предложение действительно для новых пользователей</b>\n\n"
            "Начните прямо сейчас! 👇"
        )

        return message

    def build_referral_message(
        self,
        user_data: Dict[str, Any],
        referrer_name: str,
        discount: float,
        tariffs: List[Optional[Tariff]] = None,
    ) -> str:
        """Построение сообщения о реферальном бонусе"""
        if not tariffs:
            tariffs = []

        message = (
            f"🎉 <b>Вас пригласил {referrer_name}!</b>\n\n"
            f"🎁 <b>Специальный бонус для вас: {discount}% скидка!</b>\n\n"
        )

        if discount > 0:
            message += (
                f"🔥 <b>Ваши преимущества:</b>\n"
                f"• 🆓 <b>Пробный период 7 дней + 10 ГБ</b>\n"
                f"• 💰 <b>Скидка {discount}% на все тарифы после триала</b>\n"
                f"• ⚡ <b>Приоритетная техподдержка</b>\n\n"
            )

        if tariffs:
            message += "💰 <b>Тарифы со скидкой:</b>\n\n"
            for tariff in tariffs[:3]:  # Показываем не более 3 тарифов
                original_price = tariff.amount
                discounted_price = original_price - (original_price * (discount / 100))

                message += (
                    f"🏷️ <b>{tariff.name_tariff}</b>\n"
                    f"   📦 {tariff.description}\n"
                    f"   💰 <s>{original_price}₽</s> → <b>{discounted_price:.0f}₽</b>\n"
                    f"   🔥 Экономия: {original_price - discounted_price:.0f}₽\n"
                    f"   ────────────────────\n"
                )

        message += (
            "\n🎯 <b>Как получить бонус:</b>\n"
            "1. Активируйте пробный период\n"
            "2. Используйте сервис 7 дней бесплатно\n"
            "3. После триала получите скидку при продлении\n\n"
            "⏳ <b>Предложение действительно 30 дней</b>\n\n"
            "Не упустите возможность сэкономить! 👇"
        )

        return message

    def build_upsell_message(
        self,
        user_data: Dict[str, Any],
        current_tariff: Optional[Tariff],
        premium_tariffs: List[Tariff],
    ) -> str:
        """Сообщение для апсела"""
        if not premium_tariffs:
            return ""

        message = (
            "🚀 <b>Готовы к большему?</b>\n\n"
            "Мы заметили, что вы активно пользуетесь нашим сервисом! "
            "Предлагаем перейти на премиум тарифы с улучшенными возможностями:\n\n"
        )

        for i, tariff in enumerate(premium_tariffs, 1):
            message += (
                f"{i}. <b>{tariff.name_tariff}</b> - {tariff.amount}₽/мес\n"
                f"   {tariff.description}\n"
                f"   📊 Трафик: {tariff.traffic_limit} ГБ\n"
                f"   🌐 Устройства: {tariff.limit_ip} одновременно\n\n"
            )

        if current_tariff:
            message += (
                f"💡 Сейчас вы используете: {current_tariff.name_tariff}\n"
                f"Переход займет всего пару минут! ⏱️\n\n"
                "Хотите узнать больше о преимуществах? 👇"
            )
        else:
            message += "Переход займет всего пару минут! ⏱️\n\nХотите узнать больше? 👇"

        return message

    def build_winback_message(self, user_data: Dict[str, Any]) -> str:
        """Сообщение для возврата пользователей"""
        return (
            "👋 <b>Мы скучаем по вам!</b>\n\n"
            "Заметили, что вы давно не пользовались нашим сервисом. "
            "Хотите вернуться? Для вас специальное предложение:\n\n"
            "🎁 <b>Скидка 20% на первый месяц</b>\n"
            "🆓 <b>+5 ГБ дополнительного трафика</b>\n\n"
            "Все ваши настройки и ключи сохранены и готовы к работе! "
            "Вернитесь и оцените наши улучшения! ✨\n\n"
            "Воспользоваться предложением? 👇"
        )

    def build_cross_sell_message(self, user_data: Dict[str, Any]) -> str:
        """Сообщение для кроссела (дополнительные услуги)"""
        return (
            "🌟 <b>Откройте для себя больше возможностей!</b>\n\n"
            "Как активный пользователь, вы можете получить:\n\n"
            "🔒 <b>Премиум поддержка 24/7</b>\n"
            "   Приоритетная техподдержка и быстрые ответы\n\n"
            "🌍 <b>Дополнительные серверы</b>\n"
            "   Доступ к эксклюзивным локациям по всему миру\n\n"
            "📊 <b>Расширенная статистика</b>\n"
            "   Подробные отчеты об использовании трафика\n\n"
            "Интересует какая-то из услуг? Узнайте подробности! 👇"
        )

    # В services/notification/utils_bot/message_builder.py добавляем:
