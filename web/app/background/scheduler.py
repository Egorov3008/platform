"""Фоновые задачи (Background Tasks) для VPN Backend.

Использует APScheduler для периодического запуска:
- Синхронизация кеша (каждые 3 часа)
- Цикл уведомлений об истечении ключей (каждый час)
"""

import asyncpg
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.core.logging import get_logger

logger = get_logger(__name__)

_scheduler: AsyncIOScheduler = None


def init_scheduler() -> AsyncIOScheduler:
    """Инициализировать и запустить scheduler."""
    global _scheduler
    _scheduler = AsyncIOScheduler()
    _scheduler.start()
    logger.info("[Scheduler] APScheduler инициализирован и запущен")
    return _scheduler


def add_jobs(pool: asyncpg.Pool):
    """Добавить фоновые задачи в scheduler."""
    if not _scheduler:
        raise RuntimeError("Scheduler not initialized. Call init_scheduler() first.")

    # Синхронизация данных каждые 3 часа
    _scheduler.add_job(
        sync_data_from_db,
        "interval",
        hours=3,
        args=[pool],
        id="sync_data_from_db",
        replace_existing=True,
    )
    logger.info("[Scheduler] Добавлена задача: синхронизация данных (каждые 3 часа)")

    # Отправка уведомлений каждый час
    _scheduler.add_job(
        send_expiry_notifications,
        "interval",
        hours=1,
        args=[pool],
        id="send_expiry_notifications",
        replace_existing=True,
    )
    logger.info("[Scheduler] Добавлена задача: уведомления об истечении (каждый час)")


def shutdown_scheduler():
    """Остановить scheduler."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("[Scheduler] APScheduler остановлен")


# === Background Jobs ===


async def sync_data_from_db(pool: asyncpg.Pool):
    """Синхронизировать данные из БД (перезагрузить кеши и справочники)."""
    try:
        logger.info("[Background] Начало синхронизации данных из БД")

        async with pool.acquire() as conn:
            # Примечание: в production можно добавить кеш-слой (Redis, etc)
            # Здесь просто логируем что задача выполняется
            users_count = await conn.fetchval("SELECT COUNT(*) FROM users")
            keys_count = await conn.fetchval("SELECT COUNT(*) FROM keys")

            logger.info(
                "[Background] Синхронизация завершена",
                users=users_count,
                keys=keys_count,
            )
    except Exception as e:
        logger.error("[Background] Ошибка при синхронизации данных", error=str(e))


async def send_expiry_notifications(pool: asyncpg.Pool):
    """Отправить уведомления об истечении ключей (через Telegram bot).

    Логика:
    1. Найти ключи, которые заканчиваются в течение 24 часов
    2. Пометить их флагом notified_24h в БД
    3. В реальной системе отправить сообщение через Telegram бота

    Примечание: в настоящий момент это placeholder.
    Интеграция с Bot_3xui_vpn требует отдельного bot instance или callback.
    """
    try:
        logger.info("[Background] Начало цикла уведомлений об истечении ключей")

        async with pool.acquire() as conn:
            # Найти ключи, которые заканчиваются в течение 24 часов
            keys = await conn.fetch("""
                SELECT tg_id, client_id, expiry_time
                FROM keys
                WHERE expiry_time < EXTRACT(EPOCH FROM NOW() + INTERVAL '24 hours') * 1000
                AND notified_24h = FALSE
                LIMIT 100
            """)

            if keys:
                logger.info(
                    "[Background] Найдено ключей для уведомления",
                    count=len(keys),
                )
                # TODO: Отправить уведомления через Telegram bot
                # Пример: await telegram_bot.send_message(tg_id, "Ваш ключ заканчивается...")
                # Затем обновить флаг notified_24h = TRUE
            else:
                logger.debug("[Background] Нет ключей для уведомления")

        logger.info("[Background] Цикл уведомлений завершен")
    except Exception as e:
        logger.error("[Background] Ошибка при отправке уведомлений", error=str(e))
