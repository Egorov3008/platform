import asyncio
import uuid

import asyncpg
from aiohttp import web
from punq import Container
from yookassa import Configuration, Payment
from yookassa.domain.common import SecurityHelper
from yookassa.domain.notification import (
    WebhookNotificationEventType,
    WebhookNotificationFactory,
)

from client import XUISession
from config import YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY, WEBHOOK_PATH, DISABLE_WEBHOOK_IP_CHECK

from logger import logger, with_context
from services.conteiner.app import get_container
from services.core.payment.router import PaymentRouter
from services.metrics.registry import (
    payment_total,
    payment_amount_rub_total,
    payment_processing_duration,
    webhook_requests_total,
)

# Конфигурация ЮKassa (замените на свои данные)
Configuration.account_id = YOOKASSA_SHOP_ID
Configuration.secret_key = YOOKASSA_SECRET_KEY

# Создание приложения aiohttp
app = web.Application()


# --- Обработчики событий ---
class HandlersPayment:
    """Обработчики событий."""

    def __init__(
        self,
        xui_session: XUISession,
        db_pool: asyncpg.Pool,
        payment_processor: PaymentRouter,
    ):
        self.xui_session = xui_session
        self.db_pool = db_pool
        self.payment_processor = payment_processor

    @with_context(module="payments", operation="webhook")
    async def handle_payment_succeeded(self, payment: Payment):
        """Обработка успешного платежа."""
        import time

        payment_id = payment.id
        amount = payment.amount.value

        logger.info("Оплата прошла успешно", payment_id=payment_id, amount=amount)

        t0 = time.monotonic()
        operation = "unknown"
        try:
            await self.payment_processor.route(payment_id)
            # Определяем операцию из processor после route()
            pt = self.payment_processor.processor.payment_type or ""
            operation = pt.split("|", 1)[0] if "|" in pt else "unknown"

            payment_total.labels(status="succeeded", operation=operation).inc()
            payment_amount_rub_total.labels(operation=operation).inc(float(amount))

        except Exception as e:
            payment_total.labels(status="error", operation=operation).inc()
            logger.error(
                "Возникла ошибка при обработке платежа",
                error=str(e),
                error_type=type(e).__name__,
                payment_id=payment_id,
            )
        finally:
            elapsed = time.monotonic() - t0
            payment_processing_duration.labels(operation=operation).observe(elapsed)

    async def handle_payment_waiting(self, payment: Payment):
        """Обработка платежа, ожидающего подтверждения."""
        logger.info(
            "Payment waiting for capture",
            payment_id=payment.id,
            amount=payment.amount.value
        )
        idempotence_key = str(uuid.uuid4())
        logger.info(
            "Подтверждение платежа",
            payment_id=payment.id,
            amount=payment.amount.value
        )

        response = await asyncio.to_thread(
            Payment.capture,
            payment.id,
            {"amount": {"value": f"{payment.amount.value:.2f}", "currency": "RUB"}},
            idempotence_key,
        )

        success = response.status == "succeeded"
        logger.info(
            "Платеж подтвержден",
            payment_id=payment.id,
            success=success
        )

    async def handle_payment_canceled(self, payment: Payment):
        """Обработка отмененного платежа."""
        logger.warning(
            "Payment canceled",
            payment_id=payment.id,
            reason=payment.cancellation_details.reason
        )
        try:
            await self.payment_processor.processor.load_payment_data(payment.id)
            await self.payment_processor.processor.update_payment(
                payment.id, status="canceled"
            )
            payment_total.labels(status="canceled", operation="unknown").inc()
        except Exception as e:
            logger.error(
                "Ошибка обновления статуса отменённого платежа",
                payment_id=payment.id,
                error=str(e),
            )

    async def handle_refund_succeeded(self, refund):
        """Обработка успешного возврата платежа."""
        logger.info(
            "Refund succeeded",
            refund_id=refund.id,
            payment_id=refund.payment_id
        )


class WebhookService:
    """Сервис обработки вебхуков."""

    def __init__(self, container: Container):
        self.container = container

    async def yookassa_webhook(self, request):
        """Обрабатывает вебхуки от YooKassa."""
        # 1. Проверка IP (отключается через DISABLE_WEBHOOK_IP_CHECK для dev-тестирования)
        ip = self.get_client_ip(request)
        if not DISABLE_WEBHOOK_IP_CHECK and not SecurityHelper().is_ip_trusted(ip):
            logger.warning("Untrusted IP detected", ip=ip)
            webhook_requests_total.labels(event_type="untrusted_ip", status="rejected").inc()
            return web.Response(status=400)
        if DISABLE_WEBHOOK_IP_CHECK:
            logger.warning("IP-проверка вебхука отключена (DISABLE_WEBHOOK_IP_CHECK=true)", ip=ip)

        # 2. Парсинг JSON
        try:
            event_json = await request.json()
            if not event_json:
                raise ValueError("Empty JSON data")

            # 3. Создание объекта уведомления
            notification = WebhookNotificationFactory().create(event_json)
            event_type_str = str(notification.event) if notification.event else "unknown"
            response_object = notification.object
            handlers = self.container.resolve(HandlersPayment)
            # 4. Обработка событий
            event_handlers = {
                WebhookNotificationEventType.PAYMENT_SUCCEEDED: handlers.handle_payment_succeeded,
                WebhookNotificationEventType.PAYMENT_WAITING_FOR_CAPTURE: handlers.handle_payment_waiting,
                WebhookNotificationEventType.PAYMENT_CANCELED: handlers.handle_payment_canceled,
                WebhookNotificationEventType.REFUND_SUCCEEDED: handlers.handle_refund_succeeded,
            }
            handler = event_handlers.get(notification.event)
            if handler:
                await handler(response_object)
                webhook_requests_total.labels(event_type=event_type_str, status="ok").inc()
            else:
                logger.warning("Unhandled event type", event_type=notification.event)
                webhook_requests_total.labels(event_type=event_type_str, status="unhandled").inc()
                return web.Response(status=400)

            return web.json_response({"status": "ok"}, status=200)
        except Exception as e:
            logger.error(
                "Webhook error",
                error_type=type(e).__name__,
                error_message=str(e),
                exc_info=True
            )
            webhook_requests_total.labels(event_type="error", status="error").inc()
            return web.Response(status=400)

    def get_client_ip(self, request):
        """Получение IP клиента с учетом прокси."""
        return request.headers.get("X-Forwarded-For", request.remote)


async def init_webhook_service():
    """Инициализация сервиса вебхуков."""
    # Создание контейнера зависимостей
    container = await get_container()
    service = WebhookService(container)
    # Регистрация маршрута для вебхука
    app.router.add_post(path=WEBHOOK_PATH, handler=service.yookassa_webhook)
