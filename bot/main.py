import asyncio
import signal
import sys

import asyncpg
from aiogram import Bot
from aiogram.exceptions import TelegramNetworkError, TelegramRetryAfter, TelegramAPIError
from aiogram_dialog import setup_dialogs

from middlewares.admin_search_middleware import AdminSearchMiddleware
from middlewares.dialog_error_handler import DialogExceptionHandlerMiddleware
from services.conteiner.app import get_container
from tasks import task_manager
from bot_project import bot, dp, set_bot_commands
from handlers import router
from dialogs import setup_dialog_router
from logger import logger, setup_logging
from middlewares.xui_middleware import XUIMiddleware
from middlewares.database_mw import DatabaseMiddleware
from middlewares.dependency_injection import DependencyInjectionMiddleware
from middlewares.logging_middleware import LoggingMiddleware
from middlewares.registration_users import RegistrationUsersMiddleware
from services.cache.service import CacheService
from services.cache.loader import LoadingService
from config import METRICS_PORT
from middlewares.cache_middleware import CacheMiddleware
from services.metrics.setup import init_metrics


class WatchdogService:
    """Сервис для уведомления systemd о работоспособности"""
    
    def __init__(self):
        self.last_heartbeat = 0
        self.enabled = False
        self.notifier = None
        self._init_notifier()
    
    def _init_notifier(self):
        """Инициализация sdnotify (если доступен)"""
        try:
            import sdnotify
            self.notifier = sdnotify.SystemdNotifier()
        except ImportError:
            self.notifier = None
    
    def enable(self):
        self.enabled = True
    
    async def heartbeat(self):
        """Отправка heartbeat в systemd"""
        if not self.enabled:
            return
        
        try:
            if self.notifier:
                self.notifier.notify("WATCHDOG=1")
            else:
                # Альтернатива: запись в journal
                import time
                self.last_heartbeat = time.time()
        except Exception as e:
            logger.debug("Ошибка отправки heartbeat", error=str(e))
    
    async def run_watchdog_loop(self, interval=30):
        """Фоновый цикл отправки heartbeat"""
        while self.enabled:
            await self.heartbeat()
            await asyncio.sleep(interval)


watchdog = WatchdogService()


async def on_startup():
    """Действия при запуске приложения"""
    # --- Инициализация кеша ---
    container = await get_container()

    # Запускаем CacheService (фоновая очистка)
    cache_service = container.resolve(CacheService)
    await cache_service.start()
    logger.info("CacheService запущен")

    # Загружаем данные в кеш
    loader = container.resolve(LoadingService)
    await loader.loading()
    logger.info("Кэш успешно загружен из БД")

    # # Инициализируем Prometheus метрики
    # pool = container.resolve(asyncpg.Pool)
    # await init_metrics(
    #     pool=pool,
    #     cache_storage=cache_service.storage,
    #     metrics_port=METRICS_PORT,
    # )

    # Запускаем фоновые задачи
    asyncio.create_task(task_manager.start_all_tasks(container, bot))
    
    # Запускаем мониторинг ресурсов
    asyncio.create_task(monitor_resources(interval=300))  # каждые 5 минут

    logger.info("Приложение успешно запущено")


async def monitor_resources(interval: int = 300):
    """
    Мониторинг использования памяти и ресурсов.
    Логирует предупреждения при высоком потреблении памяти.
    """
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    
    while True:
        try:
            # Получаем информацию о памяти
            mem_info = process.memory_info()
            mem_percent = process.memory_percent()
            system_memory = psutil.virtual_memory()
            
            # Логируем состояние
            logger.info(
                "Мониторинг ресурсов",
                rss_mb=round(mem_info.rss / 1024 / 1024, 2),
                vms_mb=round(mem_info.vms / 1024 / 1024, 2),
                memory_percent=round(mem_percent, 2),
                system_available_mb=round(system_memory.available / 1024 / 1024, 2),
                system_percent=round(system_memory.percent, 2),
            )
            
            # Предупреждения
            if mem_percent > 80:
                logger.warning(
                    "Высокое потребление памяти!",
                    memory_percent=round(mem_percent, 2),
                    recommendation="Рассмотрите увеличение RAM или оптимизацию",
                )
            elif mem_percent > 90:
                logger.critical(
                    "КРИТИЧЕСКИ высокое потребление памяти!",
                    memory_percent=round(mem_percent, 2),
                    recommendation="Срочно требуется оптимизация или перезапуск",
                )
            
            # Информация о системе
            if system_memory.percent > 85:
                logger.warning(
                    "Система исчерпывает память",
                    system_memory_percent=round(system_memory.percent, 2),
                    available_mb=round(system_memory.available / 1024 / 1024, 2),
                )
            
        except ImportError:
            # psutil не установлен
            logger.debug("psutil не установлен, мониторинг памяти отключен")
            break
        except Exception as e:
            logger.error("Ошибка мониторинга ресурсов", error=str(e))
        
        await asyncio.sleep(interval)


async def setup_middlewares():
    """Инициализация middleware"""
    container = await get_container()

    # DI-контейнер — первым, чтобы data["container"] был доступен остальным
    di_middleware = DependencyInjectionMiddleware()
    DependencyInjectionMiddleware.container = container
    dp.update.middleware(di_middleware)
    dp.message.middleware(di_middleware)
    dp.callback_query.middleware(di_middleware)

    # Регистрируем мидлвари
    database_middleware = DatabaseMiddleware()
    dp.update.middleware(database_middleware)
    dp.message.middleware(database_middleware)
    dp.callback_query.middleware(database_middleware)

    # CacheMiddleware
    cache_middleware = container.resolve(CacheMiddleware)
    dp.update.middleware(cache_middleware)

    dp.update.middleware(XUIMiddleware())

    registration_middleware = RegistrationUsersMiddleware()
    dp.update.middleware(registration_middleware)
    dp.message.middleware(registration_middleware)
    dp.callback_query.middleware(registration_middleware)

    # AdminSearchMiddleware — перехватывает /start с search_{tg_id} для администраторов
    # Должен стоять ДО проверки подписки, чтобы администраторы могли использовать поиск
    dp.update.middleware(AdminSearchMiddleware())

    # SubscriptionMiddleware — проверка подписки на канал
    from middlewares.subscription_middleware import SubscriptionMiddleware
    subscription_middleware = SubscriptionMiddleware()
    dp.update.middleware(subscription_middleware)

    logging_middleware = LoggingMiddleware()
    dp.update.middleware(logging_middleware)
    dp.message.middleware(logging_middleware)
    dp.callback_query.middleware(logging_middleware)

    handler_error = DialogExceptionHandlerMiddleware()
    dp.update.middleware(handler_error)


async def on_shutdown():
    """Graceful shutdown: остановка задач, кеша и пула БД."""
    logger.info("Запуск процедуры остановки приложения...")

    watchdog.enabled = False

    container = await get_container()

    await task_manager.stop_all_tasks()
    logger.info("Фоновые задачи остановлены")

    cache_service: CacheService = container.resolve(CacheService)
    await cache_service.stop()
    logger.info("CacheService остановлен")

    pool: asyncpg.Pool = container.resolve(asyncpg.Pool)
    await pool.close()
    logger.info("Пул БД закрыт")

    # Сбрасываем контейнер для создания нового при следующем запуске
    from services.conteiner.app import _container
    import services.conteiner.app as app_module
    app_module._container = None
    logger.info("Контейнер зависимостей сброшен")

    logger.info("Приложение успешно остановлено")


async def main():
    """Точка входа в приложение"""
    # Обработка сигналов для graceful shutdown
    loop = asyncio.get_event_loop()

    # Включаем watchdog
    watchdog.enable()

    # Запускаем фоновый цикл heartbeat
    watchdog_task = asyncio.create_task(watchdog.run_watchdog_loop(interval=30))

    # Инициализируем логирование ОДИН раз до начала цикла
    setup_logging()
    logger.info("Логирование инициализировано перед запуском")

    max_restart_attempts = 5
    restart_count = 0

    while restart_count < max_restart_attempts:
        try:
            # Добавляем таймаут для всего on_startup (60 секунд)
            await asyncio.wait_for(on_startup(), timeout=60.0)
            await setup_middlewares()
            dp.include_router(router)
            from handlers.subscription_handler import router as subscription_router
            dp.include_router(subscription_router)
            dialog_router = await setup_dialog_router()
            dp.include_router(dialog_router)
            dp.shutdown.register(on_shutdown)
            setup_dialogs(dp)
            await set_bot_commands(bot)
            
            # Запуск polling с обработкой ошибок
            logger.info("Запуск polling бота...")
            await dp.start_polling(bot)
            logger.info("Polling завершен")
            break
            
        except TelegramRetryAfter as e:
            # Обработка ограничений Telegram (flood control)
            logger.warning(
                "Telegram flood control, ожидание",
                retry_after=e.retry_after,
                error=str(e)
            )
            restart_count += 1
            await asyncio.sleep(e.retry_after + 5)
            continue

        except TelegramAPIError as e:
            # Другие ошибки Telegram API
            logger.error(
                "Telegram API ошибка",
                error_type=type(e).__name__,
                error=str(e)
            )
            restart_count += 1
            await asyncio.sleep(10)
            continue

        except TelegramNetworkError as e:
            # Сетевая ошибка, перезапуск через 5 секунд
            logger.error(
                "Сетевая ошибка Telegram",
                error_type=type(e).__name__,
                error=str(e)
            )
            restart_count += 1
            await asyncio.sleep(5)
            continue

        except asyncio.CancelledError:
            # Задача отменена (graceful shutdown)
            logger.info("Получена отмена задачи, завершение работы")
            break

        except asyncio.TimeoutError:
            # Таймаут при инициализации
            restart_count += 1
            logger.critical(
                "Превышен таймаут инициализации (60 сек)",
                restart_attempt=restart_count,
                max_attempts=max_restart_attempts
            )
            
            if restart_count >= max_restart_attempts:
                logger.critical(
                    "Достигнуто максимальное количество перезапусков, завершение работы"
                )
                break
            
            await asyncio.sleep(10)
            continue

        except Exception as e:
            # Критическая ошибка
            restart_count += 1
            logger.critical(
                "Критическая ошибка в главном цикле",
                error_type=type(e).__name__,
                error=str(e),
                restart_attempt=restart_count,
                max_attempts=max_restart_attempts
            )
            
            if restart_count >= max_restart_attempts:
                logger.critical(
                    "Достигнуто максимальное количество перезапусков, завершение работы"
                )
                break
                
            # Пробуем перезапустить через 10 секунд
            await asyncio.sleep(10)
            continue
    
    # Отменяем watchdog task
    watchdog_task.cancel()
    try:
        await watchdog_task
    except asyncio.CancelledError:
        pass


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Приложение остановлено пользователем")
    except Exception as e:
        logger.critical(
            "Фатальная ошибка",
            error_type=type(e).__name__,
            error_message=str(e)
        )
