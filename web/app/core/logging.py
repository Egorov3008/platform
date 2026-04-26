"""Модуль настройки и инициализации логирования приложения.

Настраивает структурированное логирование с поддержкой различных уровней,
форматирования для консоли и файлового вывода, фильтрации чувствительных данных.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from app.core.config import settings


class SensitiveDataFilter(logging.Filter):
    """Фильтр для маскировки чувствительных данных в логах."""

    SENSITIVE_PATTERNS = [
        ("password", r'("password"\s*:\s*")[^"]+(")'),
        ("secret_key", r'("secret_key"\s*:\s*")[^"]+(")'),
        ("token", r'("token"\s*:\s*")[^"]+(")'),
        ("authorization", r'("Authorization"\s*:\s*")[^"]+(")'),
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, 'msg'):
            return True

        # WR-06: форматируем сообщение до маскировки, чтобы захватить значения из args
        if record.args:
            try:
                record.msg = record.getMessage()
                record.args = ()
            except Exception:
                pass

        if isinstance(record.msg, str):
            import re
            for field_name, pattern in self.SENSITIVE_PATTERNS:
                try:
                    record.msg = re.sub(pattern, r'\1***MASKED***\2', record.msg)
                except re.error:
                    pass

        return True


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    log_format: str = "detailed",
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5,
) -> None:
    """Настраивает систему логирования для всего приложения.

    Args:
        log_level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Путь к файлу логов (опционально)
        log_format: Формат логов (detailed, simple, json)
        max_bytes: Максимальный размер файла логов перед ротацией
        backup_count: Количество резервных файлов логов
    """
    # Определяем формат логов
    if log_format == "json":
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
            '"logger": "%(name)s", "message": "%(message)s", '
            '"module": "%(module)s", "function": "%(funcName)s", '
            '"line": %(lineno)d}'
        )
    elif log_format == "simple":
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    else:  # detailed (по умолчанию)
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | '
            '%(funcName)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    # Получаем числовой уровень логирования
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Настраиваем корневой логгер
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Очищаем существующие обработчики
    root_logger.handlers.clear()

    # Обработчик для консоли
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(SensitiveDataFilter())
    root_logger.addHandler(console_handler)

    # Обработчик для файла (если указан)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        file_handler.addFilter(SensitiveDataFilter())
        root_logger.addHandler(file_handler)

    # Подавляем слишком подробные логи от сторонних библиотек
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Возвращает экземпляр логгера с заданным именем.

    Args:
        name: Имя логгера (обычно __name__ модуля)

    Returns:
        Настроенный экземпляр logging.Logger
    """
    return logging.getLogger(name)
