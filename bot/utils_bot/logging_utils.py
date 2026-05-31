from typing import Any

from py3xui import AsyncApi

from logger import logger


class DatabaseLogger:
    """Утилиты для логирования работы с базой данных"""

    # Порог медленного запроса (мс)
    SLOW_QUERY_THRESHOLD_MS = 1000  # 1 секунда

    @staticmethod
    async def log_connection(pool: Any, **extra):
        """Логирование подключения к БД"""
        await logger.info(
            "Database connection established",
            pool_size=pool.get_size(),
            pool_min_size=pool.get_min_size(),
            **extra,
        )

    @staticmethod
    async def log_query_with_timing(
        query: str,
        start_time: float,
        end_time: float,
        params: tuple = None,
        **extra
    ):
        """
        Логирование запроса с замером длительности.
        Автоматически определяет медленные запросы.
        
        Args:
            query: SQL запрос
            start_time: Время начала (time.monotonic())
            end_time: Время окончания (time.monotonic())
            params: Параметры запроса
            **extra: Дополнительные поля
        """
        duration_ms = (end_time - start_time) * 1000
        query_short = query[:200] + "..." if len(query) > 200 else query
        
        if duration_ms > DatabaseLogger.SLOW_QUERY_THRESHOLD_MS:
            # Медленный запрос — warning
            await logger.warning(
                "🐌 Slow database query detected",
                query=query_short,
                duration_ms=round(duration_ms, 2),
                threshold_ms=DatabaseLogger.SLOW_QUERY_THRESHOLD_MS,
                params_count=len(params) if params else 0,
                **extra
            )
        else:
            # Нормальный запрос — debug
            await logger.debug(
                "Database query executed",
                query=query_short,
                duration_ms=round(duration_ms, 2),
                params_count=len(params) if params else 0,
                **extra
            )

    @staticmethod
    async def log_query_error(query: str, error: Exception, **extra):
        """Логирование ошибок запросов"""
        await logger.error(
            "Database query error",
            query=query[:200],
            error_type=type(error).__name__,
            error_message=str(error),
            **extra,
        )


class XUILogger:
    """Утилиты для логирования XUI API"""

    @staticmethod
    async def log_api_call(xui: AsyncApi, method: str, success: bool, **extra):
        """Логирование вызовов XUI API"""
        await logger.info(
            "XUI API call completed",
            host=xui.host if hasattr(xui, "host") else "unknown",
            method=method,
            success=success,
            **extra,
        )

    @staticmethod
    async def log_client_operation(email: str, operation: str, success: bool, **extra):
        """Логирование операций с клиентами"""
        await logger.info(
            "XUI client operation",
            client_email=email,
            operation=operation,
            success=success,
            **extra,
        )


class PaymentLogger:
    """Утилиты для логирования платежей"""

    @staticmethod
    async def log_payment_creation(amount: float, payment_id: str, **extra):
        """Логирование создания платежа"""
        await logger.info(
            "Payment created", amount=amount, payment_id=payment_id, **extra
        )

    @staticmethod
    async def log_payment_status(payment_id: str, status: str, **extra):
        """Логирование статуса платежа"""
        await logger.info(
            "Payment status update", payment_id=payment_id, status=status, **extra
        )
