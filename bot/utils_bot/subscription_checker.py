"""
Модуль проверки подписки пользователя на Telegram-канал.
"""

from typing import Any, Optional

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest

from logger import logger
from config import CHANNEL_URL

# Статусы подписки, которые считаются активной подпиской
SUBSCRIBED_STATUSES = {"member", "administrator", "creator"}

# Время кэширования статуса подписки (в секундах)
SUBSCRIPTION_CACHE_TTL = 300  # 5 минут


async def check_user_subscription(
    bot: Bot, user_id: int, cache: Optional[Any] = None
) -> bool:
    """
    Проверяет, является ли пользователь подписчиком канала.

    :param bot: Экземпляр бота для проверки
    :param user_id: Telegram ID пользователя
    :param cache: Сервис кэша для кэширования результата (CacheService)
    :return: True если пользователь подписан, False иначе
    """
    from datetime import timedelta

    # Если CHANNEL_URL не задан — считаем что подписка не требуется
    if not CHANNEL_URL:
        logger.debug("CHANNEL_URL не задан, проверка подписки пропущена")
        return True

    # Проверяем кэш
    if cache:
        try:
            # Используем storage напрямую с namespace и key
            cached = await cache.storage.get(namespace="subscription", key=str(user_id))
            if cached is not None:
                logger.debug(
                    "Статус подписки получен из кэша",
                    user_id=user_id,
                    is_subscribed=cached == "1",
                )
                return cached == "1"
        except Exception as e:
            logger.warning(
                "Ошибка при чтении кэша подписки",
                user_id=user_id,
                error=str(e),
            )

    try:
        # Получаем username канала из URL (поддерживаемые форматы):
        # https://t.me/channel_username
        # https://telegram.me/channel_username
        # @channel_username
        # channel_username
        channel_username = _extract_channel_username(CHANNEL_URL)
        if not channel_username:
            logger.error(
                "Не удалось извлечь username канала из CHANNEL_URL",
                channel_url=CHANNEL_URL,
            )
            return False

        member = await bot.get_chat_member(
            chat_id=f"@{channel_username}",
            user_id=user_id,
        )

        is_subscribed = member.status in SUBSCRIBED_STATUSES

        logger.debug(
            "Проверка подписки пользователя",
            user_id=user_id,
            channel=channel_username,
            status=member.status,
            is_subscribed=is_subscribed,
        )

        # Кэшируем только подписанных пользователей
        if cache and is_subscribed:
            try:
                await cache.storage.set(
                    namespace="subscription",
                    key=str(user_id),
                    value="1",
                    ttl=timedelta(seconds=SUBSCRIPTION_CACHE_TTL),
                )
            except Exception as e:
                logger.warning(
                    "Ошибка при записи кэша подписки",
                    user_id=user_id,
                    error=str(e),
                )

        return is_subscribed

    except TelegramBadRequest as e:
        # Пользователь не найден в канале (не подписан)
        if "USER_NOT_PARTICIPANT" in str(e):
            logger.debug(
                "Пользователь не подписан на канал",
                user_id=user_id,
                channel=CHANNEL_URL,
            )
            return False

        # Канал не найден или бот не админ в канале
        if "CHAT_NOT_FOUND" in str(e) or "BOT_NOT_IN_CHANNEL" in str(e):
            logger.error(
                "Ошибка проверки подписки: канал не найден или бот не в канале",
                channel=CHANNEL_URL,
                error=str(e),
            )
            return False

        logger.error(
            "Ошибка Telegram API при проверке подписки",
            user_id=user_id,
            error_type=type(e).__name__,
            error_message=str(e),
        )
        return False

    except Exception as e:
        logger.error(
            "Неожиданная ошибка при проверке подписки",
            user_id=user_id,
            error_type=type(e).__name__,
            error_message=str(e),
            exc_info=True,
        )
        return False


def _extract_channel_username(channel_url: str | None) -> str | None:
    """
    Извлекает username канала из URL.

    Поддерживаемые форматы:
    - https://t.me/channel_username
    - https://telegram.me/channel_username
    - @channel_username
    - channel_username

    :param channel_url: URL или username канала
    :return: Username канала без @ или None если не удалось извлечь
    """
    if not channel_url:
        return None

    channel_url = channel_url.strip()

    # Удаляем протокол и домен
    if channel_url.startswith("https://"):
        channel_url = channel_url[8:]
    elif channel_url.startswith("http://"):
        channel_url = channel_url[7:]

    # Удаляем домены telegram.me и t.me
    for domain in ("telegram.me/", "t.me/", "telegram.me", "t.me"):
        if channel_url.startswith(domain):
            channel_url = channel_url[len(domain):]
            break

    # Удаляем ведущий @
    if channel_url.startswith("@"):
        channel_url = channel_url[1:]

    # Удаляем trailing slash и параметры
    channel_url = channel_url.split("?")[0].split("/")[0]

    # Проверяем, что остался валидный username
    if channel_url and channel_url.replace("_", "").replace("-", "").isalnum():
        return channel_url

    return None
