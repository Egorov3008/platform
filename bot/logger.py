import asyncio
import json
import logging
import os
import sys
import uuid
from collections import defaultdict
from contextvars import ContextVar
from datetime import datetime, timedelta
from functools import wraps
from typing import Any

from aiogram import types
from loguru import logger as loguru_logger

# Константы путей
LOG_FOLDER = os.path.abspath("logs")
ERROR_LOG_FOLDER = os.path.abspath("logs_error")
os.makedirs(LOG_FOLDER, exist_ok=True)
os.makedirs(ERROR_LOG_FOLDER, exist_ok=True)

# Context variable для trace_id — сквозной идентификатор для трассировки запросов
trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")

# Маскировка чувствительных данных
SENSITIVE_KEYS = {
    # Секреты и ключи доступа
    "password",
    "secret",
    "credit_card",
    "api_key",
    "access_token",
    "refresh_token",
    "shop_id",
    "secret_key",
    "BOT_TOKEN",
    "ADMIN_PASSWORD",
    "DATABASE_URL",
    "YOOKASSA_SECRET_KEY",
    
    # Персональные данные (кроме email — это идентификатор клиента в 3XUI)
    "phone",
    "card_number",
    "passport",
    "ssn",
    "birth_date",
    "address",
    "full_name",
    "username",
    
    # Ключи шифрования и сессии
    "private_key",
    "encryption_key",
    "auth_token",
    "session_id",
    "cookie",
    "csrf_token",
    "pin",
    "pin_code",
}


def sanitize_data(data: Any) -> Any:
    """Маскирует чувствительные данные и проверяет сериализуемость"""
    if isinstance(data, dict):
        result = {}
        for k, v in data.items():
            if any(sensitive in k.lower() for sensitive in SENSITIVE_KEYS):
                result[k] = "***REDACTED***"
            elif is_serializable(v):
                result[k] = sanitize_data(v)
            else:
                # Преобразуем несериализуемые объекты в строки
                result[k] = str(v)
        return result
    elif isinstance(data, list):
        return [
            sanitize_data(item) if is_serializable(item) else str(item) for item in data
        ]
    elif isinstance(data, str) and any(
        sensitive in data.lower() for sensitive in SENSITIVE_KEYS
    ):
        return "***REDACTED***"
    elif not is_serializable(data):
        return str(data)
    return data


def generate_trace_id() -> str:
    """Генерирует новый trace_id если он ещё не установлен"""
    current = trace_id_var.get()
    if not current:
        new_id = str(uuid.uuid4())[:8]  # Короткий ID для читаемости
        trace_id_var.set(new_id)
        return new_id
    return current


def get_common_fields() -> dict:
    """Возвращает общие поля для всех логов"""
    return {
        "trace_id": trace_id_var.get() or generate_trace_id(),
        "service": "bot_3xui",
    }


class LogRateLimiter:
    """
    Rate limiter для логов — предотвращает спам повторяющимися сообщениями.
    
    Использование:
        logger.info("Сообщение", _rate_limit_key="unique_key", _rate_limit_secs=10)
    """
    
    def __init__(self):
        self._last_logged: dict[str, datetime] = defaultdict(lambda: datetime.min)
        self._suppressed_count: dict[str, int] = defaultdict(int)
        self._lock = asyncio.Lock()
    
    async def should_log(self, message: str, rate_limit_key: str, rate_limit_secs: int) -> tuple[bool, int]:
        """
        Проверяет, можно ли логировать сообщение.
        
        Returns:
            (should_log, suppressed_count): Кортеж с решением и количеством подавленных логов
        """
        now = datetime.now()
        key = f"{rate_limit_key}:{message}"
        
        async with self._lock:
            last_time = self._last_logged[key]
            elapsed = (now - last_time).total_seconds()
            
            if elapsed >= rate_limit_secs:
                # Можно логировать
                self._last_logged[key] = now
                suppressed = self._suppressed_count[key]
                self._suppressed_count[key] = 0
                return True, suppressed
            else:
                # Подавляем лог
                self._suppressed_count[key] += 1
                return False, 0
    
    def reset(self):
        """Сбросить состояние (для тестов)"""
        self._last_logged.clear()
        self._suppressed_count.clear()


# Глобальный rate limiter
_rate_limiter = LogRateLimiter()


class StructuredLogger:
    """Кастомный логгер с поддержкой структурированного логирования и trace_id"""

    @staticmethod
    def _extract_rate_limit_params(extra: dict) -> tuple[str | None, int]:
        """Извлекает параметры rate limiting из extra"""
        rate_limit_key = extra.pop("_rate_limit_key", None)
        rate_limit_secs = extra.pop("_rate_limit_secs", 0)
        return rate_limit_key, rate_limit_secs
    
    @staticmethod
    async def _log_with_rate_limit(
        log_func,
        message: str,
        extra: dict,
        rate_limit_key: str | None,
        rate_limit_secs: int
    ):
        """Логирование с rate limiting"""
        if rate_limit_key and rate_limit_secs > 0:
            should_log, suppressed = await _rate_limiter.should_log(
                message, rate_limit_key, rate_limit_secs
            )
            if should_log:
                if suppressed > 0:
                    extra["suppressed_logs"] = suppressed
                    extra["rate_limit_secs"] = rate_limit_secs
                log_func(message, **extra)
        else:
            log_func(message, **extra)

    @staticmethod
    def debug(message: str, **extra: Any) -> None:
        extra = sanitize_data(extra)
        extra.update(get_common_fields())
        loguru_logger.debug(message, **extra)

    @staticmethod
    def info(message: str, **extra: Any) -> None:
        extra = sanitize_data(extra)
        extra.update(get_common_fields())
        loguru_logger.info(message, **extra)

    @staticmethod
    def warning(message: str, **extra: Any) -> None:
        extra = sanitize_data(extra)
        extra.update(get_common_fields())
        loguru_logger.warning(message, **extra)

    @staticmethod
    def error(message: str, exc_info: bool = False, **extra: Any) -> None:
        extra = sanitize_data(extra)
        extra.update(get_common_fields())
        # loguru reads ``exception=True`` from opt(); passing exc_info via
        # **extra is a no-op, which is why tracebacks were missing.
        sink = loguru_logger.opt(exception=exc_info)
        sink.error(message, **extra)

    @staticmethod
    def critical(message: str, **extra: Any) -> None:
        extra = sanitize_data(extra)
        extra.update(get_common_fields())
        loguru_logger.critical(message, **extra)

    @staticmethod
    def success(message: str, **extra: Any) -> None:
        extra = sanitize_data(extra)
        extra.update(get_common_fields())
        loguru_logger.success(message, **extra)

    @staticmethod
    def exception(message: str, **extra: Any) -> None:
        extra = sanitize_data(extra)
        extra.update(get_common_fields())
        loguru_logger.opt(exception=True).error(message, **extra)
    
    # Асинхронные версии с rate limiting
    @staticmethod
    async def debug_async(message: str, _rate_limit_key: str = None, _rate_limit_secs: int = 0, **extra: Any) -> None:
        extra = sanitize_data(extra)
        extra.update(get_common_fields())
        await StructuredLogger._log_with_rate_limit(
            loguru_logger.debug, message, extra, _rate_limit_key, _rate_limit_secs
        )

    @staticmethod
    async def info_async(message: str, _rate_limit_key: str = None, _rate_limit_secs: int = 0, **extra: Any) -> None:
        extra = sanitize_data(extra)
        extra.update(get_common_fields())
        await StructuredLogger._log_with_rate_limit(
            loguru_logger.info, message, extra, _rate_limit_key, _rate_limit_secs
        )

    @staticmethod
    async def warning_async(message: str, _rate_limit_key: str = None, _rate_limit_secs: int = 0, **extra: Any) -> None:
        extra = sanitize_data(extra)
        extra.update(get_common_fields())
        await StructuredLogger._log_with_rate_limit(
            loguru_logger.warning, message, extra, _rate_limit_key, _rate_limit_secs
        )

    @staticmethod
    async def error_async(message: str, _rate_limit_key: str = None, _rate_limit_secs: int = 0, **extra: Any) -> None:
        extra = sanitize_data(extra)
        extra.update(get_common_fields())
        await StructuredLogger._log_with_rate_limit(
            loguru_logger.error, message, extra, _rate_limit_key, _rate_limit_secs
        )


# Экспортируем экземпляр логгера
logger = StructuredLogger()


def set_trace_id(trace_id: str) -> None:
    """Устанавливает trace_id для текущего контекста"""
    trace_id_var.set(trace_id)


def get_trace_id() -> str:
    """Получает текущий trace_id"""
    return trace_id_var.get()


def reset_trace_id() -> None:
    """Сбрасывает trace_id (для использования между запросами)"""
    trace_id_var.set("")


class InterceptHandler(logging.Handler):
    """Перехватчик стандартных логов Python"""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = loguru_logger.level(record.levelname).name
        except ValueError:
            level = record.levelno // 10

        # Извлекаем extra данные
        extra_data = {}
        if hasattr(record, "extra"):
            extra_data = record.extra

        loguru_logger.opt(depth=6, exception=record.exc_info).log(
            level, record.getMessage(), **extra_data
        )


def setup_logging(environment: str = None, log_format: str = None):
    """
    Настройка системы логирования.
    
    Args:
        environment: Окружение (development/production). По умолчанию из LOG_ENVIRONMENT
        log_format: Формат логов (text/json). По умолчанию из LOG_FORMAT
    """
    import os
    
    try:
        loguru_logger.remove()
        
        # Определяем окружение и формат
        env = environment or os.getenv("LOG_ENVIRONMENT", "development")
        fmt = log_format or os.getenv("LOG_FORMAT", "text")
        is_production = env.lower() == "production"
        use_json = fmt.lower() == "json"

        def format_with_caller(record):
            """Форматирование с правильным местом вызова"""
            # Получаем фрейм вызывающей функции
            import inspect

            frame = inspect.currentframe()
            caller_frame = None
            depth = 0

            # Ищем первый фрейм, который не из loguru/logger
            while frame:
                frame = frame.f_back
                if frame:
                    module_name = frame.f_globals.get("__name__", "")
                    if not any(module_name.startswith(x) for x in ["loguru", "logger"]):
                        caller_frame = frame
                        break

            if caller_frame:
                record["name"] = caller_frame.f_globals.get("__name__", "unknown")
                record["function"] = caller_frame.f_code.co_name
                record["line"] = caller_frame.f_lineno

            return True

        # Формат для файловых логов (текстовый)
        file_format = (
            "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | "
            "{name}:{function}:{line} | {message} | {extra}"
        )

        # Формат для консоли
        console_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}:{function}:{line}</cyan> | "
            "<level>{message}</level> | "
            "<magenta>{extra}</magenta>"
        )

        if use_json:
            # JSON формат для production
            json_format = "{message}"
            
            logger.info(
                "Инициализация логирования",
                environment=env,
                log_format="json",
                is_production=is_production
            )
            
            # Основной лог-файл в JSON
            loguru_logger.add(
                os.path.join(LOG_FOLDER, "application.json.log"),
                level="INFO",
                format=json_format,
                filter=format_with_caller,
                serialize=True,  # JSON сериализация
                rotation="100 MB",
                retention="30 days",
                compression="zip",
                enqueue=True,
                encoding="utf-8",
                backtrace=True,
                diagnose=True,
                catch=True,
            )

            # Лог ошибок в JSON
            loguru_logger.add(
                os.path.join(ERROR_LOG_FOLDER, "errors.json.log"),
                level="ERROR",
                format=json_format,
                filter=format_with_caller,
                serialize=True,  # JSON сериализация
                rotation="100 MB",
                retention="90 days",
                compression="zip",
                enqueue=True,
                encoding="utf-8",
                backtrace=True,
                diagnose=True,
                catch=True,
            )
        else:
            # Текстовый формат для development
            logger.info(
                "Инициализация логирования",
                environment=env,
                log_format="text",
                is_production=is_production
            )
            
            # Основной лог-файл с фильтром
            loguru_logger.add(
                os.path.join(LOG_FOLDER, "application.log"),
                level="INFO",
                format=file_format,
                filter=format_with_caller,
                rotation="3 hours",
                retention="30 days",
                compression="zip",
                enqueue=True,
                encoding="utf-8",
                backtrace=True,
                diagnose=True,
                catch=True,
            )

            # Лог ошибок
            loguru_logger.add(
                os.path.join(ERROR_LOG_FOLDER, "errors.log"),
                level="ERROR",
                format=file_format,
                filter=format_with_caller,
                rotation="1 day",
                retention="90 days",
                compression="zip",
                enqueue=True,
                encoding="utf-8",
                catch=True,
            )

        # Консольный вывод (всегда текст для удобства разработки)
        loguru_logger.add(
            sys.stderr,
            level="DEBUG",
            format=console_format,
            filter=format_with_caller,
            colorize=True,
            catch=True,
        )

        # Перехват стандартных логов
        logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

        # Настройка логгеров библиотек
        library_loggers = {
            "aiohttp": "WARNING",
            "asyncio": "WARNING",
            "httpx": "WARNING",
            "httpcore": "WARNING",
            "urllib3": "WARNING",
            "websockets": "WARNING",
            "aiogram": "INFO",
            "asyncpg": "WARNING",
            "aiogram_dialog": "INFO",
        }

        for name, level in library_loggers.items():
            lib_logger = logging.getLogger(name)
            lib_logger.handlers = [InterceptHandler()]
            lib_logger.setLevel(getattr(logging, level))
            lib_logger.propagate = False

        logger.info("Система логирования успешно инициализирована")

    except Exception as e:
        print(f"CRITICAL: Ошибка настройки логирования: {e}")
        # Минимальная настройка для консоли
        loguru_logger.add(sys.stderr, level="ERROR")
        raise


# Декораторы для логирования
def log_execution_time(func):
    """Логирует время выполнения функции"""

    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        start_time = asyncio.get_event_loop().time()
        result = await func(*args, **kwargs)
        elapsed = (asyncio.get_event_loop().time() - start_time) * 1000

        # Используем только сериализуемые данные
        logger.debug(
            "Функция выполнена",
            function_name=func.__name__,
            module_name=func.__module__,
            elapsed_ms=round(elapsed, 2),
        )
        return result

    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        start_time = datetime.now().timestamp()
        result = func(*args, **kwargs)
        elapsed = (datetime.now().timestamp() - start_time) * 1000

        # Используем только сериализуемые данные
        logger.debug(
            "Функция выполнена",
            function_name=func.__name__,
            module_name=func.__module__,
            elapsed_ms=round(elapsed, 2),
        )
        return result

    return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper


def with_context(**context_kwargs):
    """Добавляет контекст к логам внутри функции"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with loguru_logger.contextualize(**context_kwargs):
                return func(*args, **kwargs)

        return wrapper

    return decorator


# Специализированные функции логирования
async def log_aiogram_event(handler_name: str, message: types.Message, **extra):
    """Логирование событий aiogram"""
    logger.info(
        f"Aiogram event: {handler_name}",
        user_id=message.from_user.id,
        chat_id=message.chat.id,
        message_type=message.content_type,
        **extra,
    )


async def log_database_query(query: str, params: tuple = None, **extra):
    """Логирование запросов к базе данных"""
    logger.debug(
        "Database query executed",
        query=query[:200] + "..." if len(query) > 200 else query,
        params_length=len(params) if params else 0,
        **extra,
    )


async def log_xui_api_call(method: str, endpoint: str, **extra):
    """Логирование вызовов XUI API"""
    logger.info("XUI API call", api_method=method, endpoint=endpoint, **extra)


async def log_payment_event(payment_id: str, status: str, amount: float, **extra):
    """Логирование платежных событий"""
    logger.info(
        "Payment event", payment_id=payment_id, status=status, amount=amount, **extra
    )


async def log_webhook_event(event_type: str, payload: dict, **extra):
    """Логирование вебхук событий"""
    sanitized_payload = sanitize_data(payload)
    logger.info(
        "Webhook event", event_type=event_type, payload=sanitized_payload, **extra
    )


async def log_user_action(user_id: int, action: str, **extra):
    """Логирование действий пользователей"""
    logger.info("User action", user_id=user_id, action=action, **extra)


async def log_system_event(event: str, **extra):
    """Логирование системных событий"""
    logger.info("System event", event=event, **extra)


def is_serializable(obj):
    """Проверяет, можно ли объект сериализовать в JSON"""
    try:
        json.dumps(obj)
        return True
    except (TypeError, ValueError):
        return False


# Инициализация при импорте
try:
    setup_logging()
except Exception as e:
    print(f"Не удалось инициализировать логирование: {e}")
    # Продолжаем работу с базовым логированием
    loguru_logger.add(sys.stderr, level="ERROR")
