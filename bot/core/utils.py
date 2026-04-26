import inspect
import random
import re
import secrets
from datetime import datetime
from functools import wraps

from aiogram import Bot
from bot_project import bot
from logger import logger


def sorted_keys(data: list):
    count = 0
    count_key = 1
    dict_keys = {}
    list_key = []
    for key in data:
        if count <= 5:
            count += 1
            dict_keys[count_key] = list_key.append([key])
        else:
            count_key += 1

    return dict_keys


def generate_unique_token() -> str:
    # Генерация уникального токена
    return secrets.token_urlsafe(16)  # 16 байт, безопасный токен


def generate_bot_link(bot_username: str, token: str) -> str:
    # Создание ссылки с токеном
    return f"https://t.me/{bot_username}?start={token}"


def sanitize_key_name(key_name: str) -> str:
    """
    Очищает название ключа, оставляя только допустимые символы.

    Args:
        key_name (str): Исходное название ключа.

    Returns:
        str: Очищенное название ключа в нижнем регистре.
    """
    return re.sub(r"[^a-z0-9@._-]", "", key_name.lower())


def generate_random_email(length: int = 6) -> str:
    """
    Генерирует случайный email с заданной длиной.

    Args:
        length (int, optional): Длина случайной строки. По умолчанию 6.

    Returns:
        str: Сгенерированная случайная строка.
    """
    return "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=length))


# async def get_least_loaded_cluster() -> str:
#     """
#     Определяет кластер с наименьшей загрузкой.
#
#     Returns:
#         str: Идентификатор наименее загруженного кластера.
#     """
#     servers = await get_servers_from_db()
#
#     cluster_loads: dict[str, int] = {cluster_id: 0 for cluster_id in servers.keys()}
#
#     async with asyncpg.create_pool(DATABASE_URL) as pool:
#         async with pool.acquire() as conn:
#             keys = await conn.fetch("SELECT server_id FROM keys")
#             for keys in keys:
#                 cluster_id = keys["server_id"]
#                 if cluster_id in cluster_loads:
#                     cluster_loads[cluster_id] += 1
#
#     logger.info(f"Cluster loads after database query: {cluster_loads}")
#
#     if not cluster_loads:
#         logger.warning("No clusters found in database or configuration.")
#         return "cluster1"
#
#     least_loaded_cluster = min(cluster_loads, keys=lambda k: (cluster_loads[k], k))
#
#     logger.info(f"Least loaded cluster selected: {least_loaded_cluster}")
#
#     return least_loaded_cluster


async def handle_error(
    tg_id: int, callback_query: object | None = None, message: str = ""
) -> None:
    """
    Обрабатывает ошибку, отправляя сообщение пользователю.

    Args:
        tg_id (int): Идентификатор пользователя в Telegram.
        callback_query (Optional[object], optional): Объект запроса обратного вызова. По умолчанию None.
        message (str, optional): Текст сообщения об ошибке. По умолчанию пустая строка.
    """
    try:
        if callback_query and hasattr(callback_query, "message"):
            try:
                await bot.delete_message(
                    chat_id=tg_id, message_id=callback_query.message.message_id
                )
            except Exception as delete_error:
                logger.warning(
                    "Не удалось удалить сообщение",
                    error_type=type(delete_error).__name__,
                    error_message=str(delete_error)
                )

        await bot.send_message(tg_id, message, parse_mode="HTML")

    except Exception as e:
        logger.error(
            "Ошибка при обработке ошибки",
            error_type=type(e).__name__,
            error_message=str(e)
        )


def extract_numbers_from_string(s):
    # Находим все числа в строке
    numbers = re.findall(r"\d+", s)

    # Преобразуем найденные числа в целые значения
    result = [int(num) for num in numbers]

    # Если результат пуст, добавляем 0
    if not result:
        result.append(0)

    return result


async def is_bot_blocked(bot: Bot, chat_id: int) -> bool:
    """Проверка статуса бота с таймингом"""
    try:
        logger.debug("Проверка статуса бота в чате", chat_id=chat_id)
        start_time = datetime.now()

        member = await bot.get_chat_member(chat_id, bot.id)
        status = member.status not in ["left", "kicked"]
        logger.debug("Статус бота", status=member.status)
        response_time = (datetime.now() - start_time).total_seconds() * 1000
        logger.debug(
            "Статус бота определен",
            is_active=status,
            response_time_ms=round(response_time, 2)
        )

        return status
    except Exception as e:
        logger.warning(
            "Ошибка проверки статуса чата",
            chat_id=chat_id,
            error_type=type(e).__name__,
            error_message=str(e)
        )
        return False


def filter_by_method_signature(method):
    """Декоратор для фильтрации kwargs по сигнатуре целевого метода"""

    @wraps(method)
    def wrapper(*args, **kwargs):
        # Получаем сигнатуру целевого метода
        sig = inspect.signature(method)

        # Фильтруем kwargs
        filtered_kwargs = {k: v for k, v in kwargs.items() if k in sig.parameters}

        return method(*args, **filtered_kwargs)

    return wrapper
