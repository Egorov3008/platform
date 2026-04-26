from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from typing import Callable, Dict, Any, Awaitable, Union
from datetime import datetime
import re
import uuid

from logger import logger, set_trace_id, reset_trace_id
from services.metrics.registry import handler_duration


class LoggingMiddleware(BaseMiddleware):
    """Мидлварь для логирования событий aiogram"""

    def _get_handler_name(self, handler: Callable) -> str:
        """Извлекает читаемое имя хендлера из различных форматов"""
        try:
            if hasattr(handler, "__name__") and handler.__name__ != "<lambda>":
                return handler.__name__

            handler_str = str(handler)

            # Парсим functools.partial
            if "functools.partial" in handler_str:
                # Ищем внутреннюю функцию
                match = re.search(r"function\s+([^ ]+)\s+at", handler_str)
                if match:
                    return f"partial({match.group(1)})"

                # Ищем классы в middlewares
                middleware_match = re.search(
                    r"middlewares\.([^\.]+)\.([^>]+)", handler_str
                )
                if middleware_match:
                    return f"middleware({middleware_match.group(1)}.{middleware_match.group(2)})"

            # Парсим CallableObject
            if "CallableObject" in handler_str:
                match = re.search(r"CallableObject\.([^ ]+)", handler_str)
                if match:
                    return f"handler({match.group(1)})"

            return handler_str[:100]  # Обрезаем слишком длинные строки

        except Exception:
            return str(handler)[:100]

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Union[Message, CallbackQuery],
        data: Dict[str, Any],
    ) -> Any:
        start_time = datetime.now()
        handler_name = self._get_handler_name(handler)
        
        # Генерируем trace_id для этого события
        event_trace_id = str(uuid.uuid4())[:8]
        set_trace_id(event_trace_id)

        try:
            # Логируем входящее событие
            if isinstance(event, Message):
                log_data = {
                    "user_id": event.from_user.id,
                    "chat_id": event.chat.id,
                    "message_type": event.content_type,
                    "message_id": event.message_id,
                }

                if event.text:
                    log_data["text_preview"] = (
                        event.text[:120] + "..."
                        if len(event.text) > 120
                        else event.text
                    )

                logger.info("📥 Incoming message", **log_data, handler=handler_name)

            elif isinstance(event, CallbackQuery):
                logger.info(
                    "🖱️ Incoming callback",
                    user_id=event.from_user.id,
                    callback_data=event.data[:80] + "..."
                    if event.data and len(event.data) > 80
                    else event.data,
                    message_id=event.message.message_id if event.message else None,
                    handler=handler_name,
                )

            # Выполняем хендлер
            result = await handler(event, data)

            # Логируем успешное выполнение
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            logger.success(
                "✅ Handler completed",
                handler=handler_name,
                execution_time_ms=round(execution_time, 2),
                status="success",
            )

            # Prometheus: handler latency
            event_type = "message" if isinstance(event, Message) else "callback"
            handler_duration.labels(
                handler=handler_name, event_type=event_type, status="success"
            ).observe(execution_time / 1000)

            return result

        except Exception as e:
            # Логируем ошибку
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            logger.error(
                "❌ Handler failed",
                handler=handler_name,
                error_type=type(e).__name__,
                error_message=str(e),
                execution_time_ms=round(execution_time, 2),
                status="error",
            )

            # Prometheus: handler latency с ошибкой
            event_type = "message" if isinstance(event, Message) else "callback"
            handler_duration.labels(
                handler=handler_name, event_type=event_type, status="error"
            ).observe(execution_time / 1000)

            raise
        finally:
            # Сбрасываем trace_id после обработки события
            reset_trace_id()
