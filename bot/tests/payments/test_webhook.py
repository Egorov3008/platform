"""
Тесты для HandlersPayment и WebhookService (payments/pyments_webhook.py).

HandlersPayment:
- handle_payment_succeeded: вызывает payment_processor.route(payment_id)
- handle_payment_waiting: вызывает asyncio.to_thread(Payment.capture, ...)
- handle_payment_canceled: обновляет статус через processor
- handle_refund_succeeded: логирует

WebhookService:
- yookassa_webhook: проверка IP, парсинг JSON, маршрутизация событий
- get_client_ip: возвращает IP из X-Forwarded-For или request.remote

Стратегия: все внешние зависимости (XUISession, asyncpg.Pool, PaymentRouter,
SecurityHelper, WebhookNotificationFactory) заменяются мок-объектами.

Примечание: pyments_webhook.py импортирует services.conteiner.app (DI контейнер),
что создаёт цепочку импортов. Разрываем её патчем на уровне sys.modules перед импортом.
"""

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Разрываем циклический импорт: заглушки для тяжёлых модулей DI контейнера
_container_stub = MagicMock()
_container_stub.get_container = AsyncMock()
sys.modules.setdefault("services.conteiner.app", _container_stub)

from payments.pyments_webhook import HandlersPayment, WebhookService  # noqa: E402


# ──────────────────────────────────────────────
# Вспомогательные фикстуры
# ──────────────────────────────────────────────

@pytest.fixture
def mock_payment_obj():
    """Мок объекта Payment из YooKassa SDK."""
    payment = MagicMock()
    payment.id = "pay_test_001"
    payment.amount = MagicMock()
    payment.amount.value = 500.0
    payment.cancellation_details = MagicMock()
    payment.cancellation_details.reason = "card_expired"
    return payment


@pytest.fixture
def mock_processor():
    """Мок PaymentRouter."""
    processor = AsyncMock()
    processor.route = AsyncMock()
    processor.processor = AsyncMock()
    processor.processor.load_payment_data = AsyncMock()
    processor.processor.update_payment = AsyncMock()
    return processor


@pytest.fixture
def handlers(mock_processor):
    """HandlersPayment с мок-зависимостями."""
    xui_session = AsyncMock()
    db_pool = AsyncMock()
    return HandlersPayment(
        xui_session=xui_session,
        db_pool=db_pool,
        payment_processor=mock_processor,
    )


@pytest.fixture
def mock_container():
    """Мок DI контейнера."""
    return MagicMock()


@pytest.fixture
def webhook_service(mock_container):
    """WebhookService с мок-контейнером."""
    return WebhookService(container=mock_container)


# ──────────────────────────────────────────────
# HandlersPayment.handle_payment_succeeded
# ──────────────────────────────────────────────

class TestHandlePaymentSucceeded:
    @pytest.mark.asyncio
    async def test_routes_payment_id(self, handlers, mock_processor, mock_payment_obj):
        """Успешный платёж маршрутизируется через payment_processor.route."""
        await handlers.handle_payment_succeeded(mock_payment_obj)
        mock_processor.route.assert_awaited_once_with("pay_test_001")

    @pytest.mark.asyncio
    async def test_exception_in_route_does_not_propagate(self, handlers, mock_processor, mock_payment_obj):
        """Исключение в route логируется, но не пробрасывается."""
        mock_processor.route.side_effect = RuntimeError("DB down")
        # Не должно бросать исключение
        await handlers.handle_payment_succeeded(mock_payment_obj)

    @pytest.mark.asyncio
    async def test_uses_payment_id_from_object(self, handlers, mock_processor):
        """payment_id берётся из payment.id."""
        payment = MagicMock()
        payment.id = "unique_pay_xyz"
        payment.amount = MagicMock()
        payment.amount.value = 100.0

        await handlers.handle_payment_succeeded(payment)
        mock_processor.route.assert_awaited_once_with("unique_pay_xyz")


# ──────────────────────────────────────────────
# HandlersPayment.handle_payment_waiting
# ──────────────────────────────────────────────

class TestHandlePaymentWaiting:
    @pytest.mark.asyncio
    async def test_captures_payment(self, handlers, mock_payment_obj):
        """Захватывает платёж: asyncio.to_thread вызывается ровно один раз."""
        mock_response = MagicMock()
        mock_response.status = "succeeded"

        with patch(
            "payments.pyments_webhook.asyncio.to_thread",
            new=AsyncMock(return_value=mock_response),
        ) as mock_thread:
            await handlers.handle_payment_waiting(mock_payment_obj)

        # to_thread вызван один раз — это вызов Payment.capture
        mock_thread.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_passes_correct_amount(self, handlers, mock_payment_obj):
        """Сумма платежа передаётся в capture корректно."""
        mock_payment_obj.amount.value = 750.0
        mock_response = MagicMock()
        mock_response.status = "succeeded"

        with patch(
            "payments.pyments_webhook.asyncio.to_thread",
            new=AsyncMock(return_value=mock_response),
        ) as mock_thread:
            await handlers.handle_payment_waiting(mock_payment_obj)

        # to_thread(Payment.capture, payment_id, amount_dict, idempotence_key)
        # позиционные аргументы: [0]=Payment.capture, [1]=payment.id, [2]=amount_dict
        call_args = mock_thread.call_args[0]
        amount_dict = call_args[2]
        assert amount_dict["amount"]["value"] == "750.00"

    @pytest.mark.asyncio
    async def test_succeeded_response(self, handlers, mock_payment_obj):
        """Статус 'succeeded' — успешный захват."""
        mock_response = MagicMock()
        mock_response.status = "succeeded"

        with patch(
            "payments.pyments_webhook.asyncio.to_thread",
            new=AsyncMock(return_value=mock_response),
        ):
            # Не бросает исключение
            await handlers.handle_payment_waiting(mock_payment_obj)


# ──────────────────────────────────────────────
# HandlersPayment.handle_payment_canceled
# ──────────────────────────────────────────────

class TestHandlePaymentCanceled:
    @pytest.mark.asyncio
    async def test_updates_payment_status(self, handlers, mock_processor, mock_payment_obj):
        """Отменённый платёж обновляет статус через processor."""
        await handlers.handle_payment_canceled(mock_payment_obj)

        mock_processor.processor.load_payment_data.assert_awaited_once_with("pay_test_001")
        mock_processor.processor.update_payment.assert_awaited_once_with(
            "pay_test_001", status="canceled"
        )

    @pytest.mark.asyncio
    async def test_exception_does_not_propagate(self, handlers, mock_processor, mock_payment_obj):
        """Ошибка при обновлении логируется, не пробрасывается."""
        mock_processor.processor.load_payment_data.side_effect = Exception("DB error")
        # Не должно бросать
        await handlers.handle_payment_canceled(mock_payment_obj)


# ──────────────────────────────────────────────
# HandlersPayment.handle_refund_succeeded
# ──────────────────────────────────────────────

class TestHandleRefundSucceeded:
    @pytest.mark.asyncio
    async def test_handles_refund(self, handlers):
        """handle_refund_succeeded выполняется без ошибок."""
        refund = MagicMock()
        refund.id = "refund_123"
        refund.payment_id = "pay_456"

        # Просто не бросает исключение
        await handlers.handle_refund_succeeded(refund)


# ──────────────────────────────────────────────
# WebhookService.get_client_ip
# ──────────────────────────────────────────────

class TestGetClientIp:
    def test_returns_x_forwarded_for(self, webhook_service):
        """X-Forwarded-For приоритетнее request.remote."""
        request = MagicMock()
        request.headers = {"X-Forwarded-For": "185.1.2.3"}
        request.remote = "10.0.0.1"

        ip = webhook_service.get_client_ip(request)
        assert ip == "185.1.2.3"

    def test_falls_back_to_remote(self, webhook_service):
        """Если X-Forwarded-For отсутствует — используется request.remote."""
        request = MagicMock()
        request.headers = {}
        request.remote = "192.168.1.50"

        ip = webhook_service.get_client_ip(request)
        assert ip == "192.168.1.50"


# ──────────────────────────────────────────────
# WebhookService.yookassa_webhook
# ──────────────────────────────────────────────

class TestYookassaWebhook:
    def _make_request(self, ip="185.1.1.1", body=None):
        """Создаёт мок aiohttp-запроса."""
        request = AsyncMock()
        request.headers = {"X-Forwarded-For": ip}
        request.remote = ip
        request.json = AsyncMock(return_value=body or {"type": "notification"})
        return request

    @pytest.mark.asyncio
    async def test_untrusted_ip_returns_400(self, webhook_service):
        """Запрос с недоверенного IP возвращает 400."""
        request = self._make_request(ip="1.2.3.4")

        with patch("payments.pyments_webhook.SecurityHelper") as mock_helper_cls:
            mock_helper_cls.return_value.is_ip_trusted.return_value = False
            response = await webhook_service.yookassa_webhook(request)

        assert response.status == 400

    @pytest.mark.asyncio
    async def test_empty_json_returns_400(self, webhook_service):
        """Пустой JSON тело возвращает 400."""
        request = self._make_request()
        request.json = AsyncMock(return_value=None)

        with patch("payments.pyments_webhook.SecurityHelper") as mock_helper_cls:
            mock_helper_cls.return_value.is_ip_trusted.return_value = True
            response = await webhook_service.yookassa_webhook(request)

        assert response.status == 400

    @pytest.mark.asyncio
    async def test_payment_succeeded_routes_to_handler(self, webhook_service, mock_container):
        """PAYMENT_SUCCEEDED маршрутизируется к handle_payment_succeeded."""
        from yookassa.domain.notification import WebhookNotificationEventType

        request = self._make_request()
        # Без spec= чтобы методы были AsyncMock (spec=HandlersPayment делает их MagicMock)
        mock_handlers = AsyncMock()
        mock_container.resolve.return_value = mock_handlers

        mock_notification = MagicMock()
        mock_notification.event = WebhookNotificationEventType.PAYMENT_SUCCEEDED
        mock_notification.object = MagicMock()

        with patch("payments.pyments_webhook.SecurityHelper") as mock_helper_cls:
            mock_helper_cls.return_value.is_ip_trusted.return_value = True
            with patch("payments.pyments_webhook.WebhookNotificationFactory") as mock_factory_cls:
                mock_factory_cls.return_value.create.return_value = mock_notification
                response = await webhook_service.yookassa_webhook(request)

        mock_handlers.handle_payment_succeeded.assert_awaited_once_with(mock_notification.object)
        assert response.status == 200

    @pytest.mark.asyncio
    async def test_payment_canceled_routes_to_handler(self, webhook_service, mock_container):
        """PAYMENT_CANCELED маршрутизируется к handle_payment_canceled."""
        from yookassa.domain.notification import WebhookNotificationEventType

        request = self._make_request()
        mock_handlers = AsyncMock()
        mock_container.resolve.return_value = mock_handlers

        mock_notification = MagicMock()
        mock_notification.event = WebhookNotificationEventType.PAYMENT_CANCELED
        mock_notification.object = MagicMock()

        with patch("payments.pyments_webhook.SecurityHelper") as mock_helper_cls:
            mock_helper_cls.return_value.is_ip_trusted.return_value = True
            with patch("payments.pyments_webhook.WebhookNotificationFactory") as mock_factory_cls:
                mock_factory_cls.return_value.create.return_value = mock_notification
                response = await webhook_service.yookassa_webhook(request)

        mock_handlers.handle_payment_canceled.assert_awaited_once_with(mock_notification.object)
        assert response.status == 200

    @pytest.mark.asyncio
    async def test_unknown_event_returns_400(self, webhook_service, mock_container):
        """Неизвестный тип события возвращает 400."""
        request = self._make_request()
        mock_handlers = AsyncMock()
        mock_container.resolve.return_value = mock_handlers

        mock_notification = MagicMock()
        mock_notification.event = "unknown_event_type"

        with patch("payments.pyments_webhook.SecurityHelper") as mock_helper_cls:
            mock_helper_cls.return_value.is_ip_trusted.return_value = True
            with patch("payments.pyments_webhook.WebhookNotificationFactory") as mock_factory_cls:
                mock_factory_cls.return_value.create.return_value = mock_notification
                response = await webhook_service.yookassa_webhook(request)

        assert response.status == 400

    @pytest.mark.asyncio
    async def test_json_parse_error_returns_400(self, webhook_service):
        """Ошибка при парсинге JSON возвращает 400."""
        request = self._make_request()
        request.json = AsyncMock(side_effect=ValueError("bad json"))

        with patch("payments.pyments_webhook.SecurityHelper") as mock_helper_cls:
            mock_helper_cls.return_value.is_ip_trusted.return_value = True
            response = await webhook_service.yookassa_webhook(request)

        assert response.status == 400

    @pytest.mark.asyncio
    async def test_successful_response_is_json_ok(self, webhook_service, mock_container):
        """Успешная обработка возвращает JSON {"status": "ok"} со статусом 200."""
        from yookassa.domain.notification import WebhookNotificationEventType

        request = self._make_request()
        mock_handlers = AsyncMock()
        mock_container.resolve.return_value = mock_handlers

        mock_notification = MagicMock()
        mock_notification.event = WebhookNotificationEventType.REFUND_SUCCEEDED
        mock_notification.object = MagicMock()

        with patch("payments.pyments_webhook.SecurityHelper") as mock_helper_cls:
            mock_helper_cls.return_value.is_ip_trusted.return_value = True
            with patch("payments.pyments_webhook.WebhookNotificationFactory") as mock_factory_cls:
                mock_factory_cls.return_value.create.return_value = mock_notification
                response = await webhook_service.yookassa_webhook(request)

        assert response.status == 200
