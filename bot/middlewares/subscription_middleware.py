"""
Middleware для проверки подписки пользователя на Telegram-канал.

Проверяет подписку только для зарегистрированных пользователей.
Не блокирует flow регистрации (captcha, gift, referral).
"""

from typing import Callable, Dict, Any, Awaitable, Optional
import json

from aiogram import BaseMiddleware, Bot
from aiogram.types import TelegramObject, Update

from logger import logger
from config import CHANNEL_URL
from utils_bot.subscription_checker import check_user_subscription
from utils_bot.subscription_keyboard import create_subscription_keyboard


class SubscriptionMiddleware(BaseMiddleware):
    """
    Middleware для обязательной проверки подписки на канал.

    Логика работы:
    1. Если CHANNEL_URL не задан — пропускает всех
    2. Если пользователь не зарегистрирован — пропускает (регистрация впереди)
    3. Если пользователь зарегистрирован:
       - Проверяет подписку через check_user_subscription()
       - Если подписан — пропускает дальше
       - Если не подписан — отправляет сообщение с кнопкой подписки
         и останавливает обработку (не вызывает handler)

    Не блокирует:
    - Команду /start с токенами (gift, referral) — обработка в RegistrationUsersMiddleware
    - Состояние Register.captcha — регистрация нового пользователя
    """

    def __init__(self):
        pass

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # Если CHANNEL_URL не задан — пропускаем всех
        if not CHANNEL_URL:
            logger.info("CHANNEL_URL не задан — пропускаем всех")
            return await handler(event, data)

        # Получаем данные из middleware
        user = data.get("event_from_user")
        if not user:
            logger.info("event_from_user не найден — пропускаем")
            return await handler(event, data)

        user_id = user.id
        cache = data.get("cache")
        bot: Optional[Bot] = data.get("bot")

        if not bot:
            logger.error("Bot не найден в data middleware")
            return await handler(event, data)

        update = event if isinstance(event, Update) else None

        logger.info(
            "SubscriptionMiddleware вызван",
            user_id=user_id,
            username=user.username,
            event_type=event.__class__.__name__,
        )

        # Проверяем, зарегистрирован ли пользователь
        is_registered = await self._check_registration(user_id, cache, data)
        logger.info(
            "Проверка регистрации",
            user_id=user_id,
            is_registered=is_registered,
        )

        # Если пользователь не зарегистрирован — пропускаем (регистрация впереди)
        if not is_registered:
            logger.info("Пользователь не зарегистрирован — пропускаем")
            return await handler(event, data)

        # Пропускаем callback проверки подписки — иначе handler никогда не вызовется
        if update and update.callback_query and update.callback_query.data == "subscription_check":
            return await handler(event, data)

        # Проверяем, не находится ли пользователь в процессе регистрации (captcha)
        in_registration = await self._is_in_registration_process(update, data, user_id)
        if in_registration:
            logger.info("Пользователь в процессе регистрации — пропускаем")
            return await handler(event, data)

        # Проверяем подписку
        is_subscribed = await check_user_subscription(bot, user_id, cache)
        logger.info(
            "Проверка подписки",
            user_id=user_id,
            is_subscribed=is_subscribed,
        )

        if is_subscribed:
            # Пользователь подписан — пропускаем дальше
            logger.info("Пользователь подписан — пропускаем дальше")
            return await handler(event, data)

        # Пользователь не подписан — отправляем уведомление
        logger.warning(
            "Пользователь не подписан — блокируем доступ",
            user_id=user_id,
        )
        # Сохраняем контекст для возврата после подписки
        await self._save_subscription_context(cache, user_id, update)
        await self._notify_subscription_required(bot, user_id)

        # Не вызываем handler — блокируем доступ до подписки
        return None

    async def _check_registration(
        self, user_id: int, cache: Any, data: Dict[str, Any]
    ) -> bool:
        """
        Проверяет, зарегистрирован ли пользователь через backend API.
        """
        try:
            from api.backend_client import BackendAPIClient

            container = data.get("container")
            if container:
                backend = container.resolve(BackendAPIClient)
                user = await backend.get_user(user_id)
                if user:
                    return True
        except Exception as e:
            logger.debug(
                "Ошибка при проверке пользователя в backend",
                user_id=user_id,
                error=str(e),
            )

        return False

    async def _is_in_registration_process(
        self, event: Optional[Update], data: Dict[str, Any], user_id: int
    ) -> bool:
        """
        Проверяет, находится ли пользователь в процессе регистрации.

        Пропускаем:
        - Команду /start с токенами (gift, referral) — только в этом же событии
        - Состояние Register.captcha
        """
        # Проверяем, есть ли результат регистрации из RegistrationUsersMiddleware
        registration_result = data.get("registration_result")
        if registration_result and isinstance(registration_result, dict):
            reg_type = registration_result.get("type")
            # Пропускаем gift и referral регистрацию
            # Но только если это команда /start (первое сообщение после регистрации)
            if reg_type in ("gift", "referral") and event is not None:
                message = event.message or event.edited_message
                if message and message.text and message.text.startswith("/start"):
                    logger.debug(
                        "Пропускаем проверку подписки — только что зарегистрирован",
                        user_id=user_id,
                        reg_type=reg_type,
                    )
                    return True

        # Проверяем состояние через FSMContext
        try:
            from aiogram.fsm.context import FSMContext

            state: Optional[FSMContext] = data.get("state")
            if state:
                current_state = await state.get_state()
                if current_state and "Register:captcha" in current_state:
                    return True
        except Exception:
            # Если не удалось получить состояние — не блокируем
            pass

        return False

    async def _notify_subscription_required(self, bot: Bot, user_id: int) -> None:
        """
        Отправляет пользователю сообщение с просьбой подписаться на канал.
        """
        keyboard = create_subscription_keyboard()

        message_text = (
            "🔒 <b>Доступ ограничен</b>\n\n"
            "Для использования бота необходимо подписаться на наш канал:\n\n"
            "👇 Нажмите кнопку ниже, чтобы подписаться, а затем подтвердите подписку"
        )

        try:
            await bot.send_message(
                chat_id=user_id,
                text=message_text,
                reply_markup=keyboard,
                parse_mode="HTML",
            )
            logger.debug(
                "Отправлено уведомление о необходимости подписки",
                user_id=user_id,
            )
        except Exception as e:
            logger.error(
                "Ошибка при отправке уведомления о подписке",
                user_id=user_id,
                error_type=type(e).__name__,
                error_message=str(e),
            )

    async def _save_subscription_context(
        self, cache: Any, user_id: int, event: Optional[Update]
    ) -> None:
        """
        Сохраняет контекст действия, которое пользователь хотел совершить.

        Нужно для возврата пользователя к исходному действию после подписки.
        """
        from datetime import timedelta

        if not cache or not event:
            return

        context: Dict[str, Any] = {
            "callback_data": None,
            "message_text": None,
            "event_type": None,
        }

        # Сохраняем callback_data если это callback_query
        if event.callback_query:
            context["callback_data"] = event.callback_query.data
            context["event_type"] = "callback_query"

        # Сохраняем текст сообщения если это message
        if event.message:
            context["message_text"] = event.message.text
            context["event_type"] = "message"

        try:
            await cache.storage.set(
                namespace="subscription",
                key=f"return_to:{user_id}",
                value=json.dumps(context),
                ttl=timedelta(seconds=300),  # 5 минут
            )
            logger.debug(
                "Сохранён контекст для возврата после подписки",
                user_id=user_id,
                context=context,
            )
        except Exception as e:
            logger.warning(
                "Ошибка при сохранении контекста подписки",
                user_id=user_id,
                error=str(e),
            )
