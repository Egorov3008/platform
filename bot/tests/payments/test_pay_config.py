"""
Тесты для YooKassService (payments/pay_config.py).

Покрытие:
- _data_payment: формирование словаря для YooKassa API
- _create_payment: вызов asyncio.to_thread(Payment.create, ...)
- create_payment_form: публичный API
- _get_succeeded: вызов asyncio.to_thread(Payment.capture, ...)
- get_waiting_for_capture: проверка статуса
- _get_status: вызов asyncio.to_thread(Payment.find_one, ...)

Стратегия мокирования: патчим Payment через "payments.pay_config.Payment".
asyncio.to_thread патчим через "payments.pay_config.asyncio.to_thread"
чтобы функция выполнялась синхронно в тестах.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from payments.pay_config import YooKassService


@pytest.fixture
def service():
    return YooKassService()


# ──────────────────────────────────────────────
# _data_payment
# ──────────────────────────────────────────────
class TestDataPayment:
    def test_amount_formatted_correctly(self, service):
        """Сумма форматируется до двух знаков после запятой."""
        data = service._data_payment(100.5, "test")
        assert data["amount"]["value"] == "100.50"
        assert data["amount"]["currency"] == "RUB"

    def test_description_stored(self, service):
        """Описание сохраняется в данных платежа."""
        data = service._data_payment(50.0, "Услуга VPN")
        assert data["description"] == "Услуга VPN"

    def test_capture_false(self, service):
        """capture=False — двухстадийный платёж."""
        data = service._data_payment(200.0, "desc")
        assert data["capture"] is False

    def test_payment_method_bank_card(self, service):
        """Тип оплаты — банковская карта."""
        data = service._data_payment(99.0, "desc")
        assert data["payment_method_data"]["type"] == "bank_card"

    def test_confirmation_type_redirect(self, service):
        """Тип подтверждения — редирект."""
        data = service._data_payment(99.0, "desc")
        assert data["confirmation"]["type"] == "redirect"

    def test_receipt_contains_item(self, service):
        """Чек содержит один товар."""
        data = service._data_payment(150.0, "desc")
        items = data["receipt"]["items"]
        assert len(items) == 1
        assert items[0]["amount"]["value"] == "150.00"
        assert items[0]["amount"]["currency"] == "RUB"

    def test_integer_price_formatted(self, service):
        """Целая цена форматируется корректно."""
        data = service._data_payment(500, "desc")
        assert data["amount"]["value"] == "500.00"


# ──────────────────────────────────────────────
# _create_payment
# ──────────────────────────────────────────────
class TestCreatePayment:
    @pytest.mark.asyncio
    async def test_happy_path_returns_ids(self, service):
        """Успешное создание: возвращает payment_id и confirmation_url."""
        mock_payment = MagicMock()
        mock_payment.id = "pay_123"
        mock_payment.confirmation.confirmation_url = "https://pay.yookassa.ru/confirm"

        with patch("payments.pay_config.asyncio.to_thread", new=AsyncMock(return_value=mock_payment)):
            result = await service._create_payment(100.0, {}, "idem-key-1")

        assert result["payment_id"] == "pay_123"
        assert result["confirmation_url"] == "https://pay.yookassa.ru/confirm"

    @pytest.mark.asyncio
    async def test_confirmations_list_fallback(self, service):
        """Fallback: если confirmation None, используется confirmations[0]."""
        mock_payment = MagicMock()
        mock_payment.id = "pay_456"
        mock_payment.confirmation = None
        mock_conf = MagicMock()
        mock_conf.confirmation_url = "https://pay.yookassa.ru/alt"
        mock_payment.confirmations = [mock_conf]

        with patch("payments.pay_config.asyncio.to_thread", new=AsyncMock(return_value=mock_payment)):
            result = await service._create_payment(200.0, {}, "idem-key-2")

        assert result["confirmation_url"] == "https://pay.yookassa.ru/alt"

    @pytest.mark.asyncio
    async def test_missing_confirmation_url_raises(self, service):
        """Если confirmation_url отсутствует — бросает ValueError."""
        mock_payment = MagicMock()
        mock_payment.id = "pay_789"
        mock_payment.confirmation = None
        mock_payment.confirmations = []

        with patch("payments.pay_config.asyncio.to_thread", new=AsyncMock(return_value=mock_payment)):
            with pytest.raises(ValueError, match="Confirmation URL not found"):
                await service._create_payment(300.0, {}, "idem-key-3")

    @pytest.mark.asyncio
    async def test_payment_api_error_propagates(self, service):
        """Исключение из Payment.create пробрасывается наружу."""
        with patch(
            "payments.pay_config.asyncio.to_thread",
            new=AsyncMock(side_effect=RuntimeError("API unavailable")),
        ):
            with pytest.raises(RuntimeError, match="API unavailable"):
                await service._create_payment(50.0, {}, "idem-key-err")


# ──────────────────────────────────────────────
# create_payment_form
# ──────────────────────────────────────────────
class TestCreatePaymentForm:
    @pytest.mark.asyncio
    async def test_calls_create_payment(self, service):
        """create_payment_form делегирует в _create_payment и возвращает его результат."""
        expected = {"payment_id": "p1", "confirmation_url": "https://url"}

        with patch.object(service, "_create_payment", new=AsyncMock(return_value=expected)) as mock_cp:
            result = await service.create_payment_form(99.0, "VPN 1 month")

        mock_cp.assert_awaited_once()
        assert result == expected

    @pytest.mark.asyncio
    async def test_passes_price_and_description(self, service):
        """Цена и описание передаются в _data_payment."""
        expected = {"payment_id": "p2", "confirmation_url": "https://u2"}

        with patch.object(service, "_create_payment", new=AsyncMock(return_value=expected)):
            with patch.object(service, "_data_payment", wraps=service._data_payment) as mock_dp:
                await service.create_payment_form(150.0, "Оплата VPN")

        mock_dp.assert_called_once_with(150.0, "Оплата VPN")

    @pytest.mark.asyncio
    async def test_error_propagates(self, service):
        """Ошибка из _create_payment пробрасывается наружу."""
        with patch.object(
            service, "_create_payment", new=AsyncMock(side_effect=ValueError("fail"))
        ):
            with pytest.raises(ValueError, match="fail"):
                await service.create_payment_form(50.0, "desc")


# ──────────────────────────────────────────────
# _get_succeeded
# ──────────────────────────────────────────────
class TestGetSucceeded:
    @pytest.mark.asyncio
    async def test_succeeded_status_returns_true(self, service):
        """Статус 'succeeded' → возвращает True."""
        mock_resp = MagicMock()
        mock_resp.status = "succeeded"

        with patch("payments.pay_config.asyncio.to_thread", new=AsyncMock(return_value=mock_resp)):
            result = await service._get_succeeded("pay_ok", 100.0)

        assert result is True

    @pytest.mark.asyncio
    async def test_non_succeeded_status_returns_false(self, service):
        """Статус не 'succeeded' → возвращает False."""
        mock_resp = MagicMock()
        mock_resp.status = "canceled"

        with patch("payments.pay_config.asyncio.to_thread", new=AsyncMock(return_value=mock_resp)):
            result = await service._get_succeeded("pay_canceled", 100.0)

        assert result is False

    @pytest.mark.asyncio
    async def test_exception_returns_false(self, service):
        """Исключение при capture → возвращает False (не пробрасывает)."""
        with patch(
            "payments.pay_config.asyncio.to_thread",
            new=AsyncMock(side_effect=Exception("network error")),
        ):
            result = await service._get_succeeded("pay_err", 50.0)

        assert result is False


# ──────────────────────────────────────────────
# get_waiting_for_capture
# ──────────────────────────────────────────────
class TestGetWaitingForCapture:
    @pytest.mark.asyncio
    async def test_waiting_status_returned(self, service):
        """Статус 'waiting_for_capture' возвращается как строка."""
        with patch.object(service, "_get_status", new=AsyncMock(return_value="waiting_for_capture")):
            result = await service.get_waiting_for_capture("pay_wait")

        assert result == "waiting_for_capture"

    @pytest.mark.asyncio
    async def test_other_status_returns_none(self, service):
        """Любой другой статус → возвращает None."""
        with patch.object(service, "_get_status", new=AsyncMock(return_value="pending")):
            result = await service.get_waiting_for_capture("pay_pend")

        assert result is None

    @pytest.mark.asyncio
    async def test_exception_returns_none(self, service):
        """Исключение в _get_status → возвращает None."""
        with patch.object(
            service, "_get_status", new=AsyncMock(side_effect=Exception("fail"))
        ):
            result = await service.get_waiting_for_capture("pay_fail")

        assert result is None

    @pytest.mark.asyncio
    async def test_succeeded_status_returns_none(self, service):
        """Статус 'succeeded' → возвращает None (платёж уже захвачен)."""
        with patch.object(service, "_get_status", new=AsyncMock(return_value="succeeded")):
            result = await service.get_waiting_for_capture("pay_done")

        assert result is None


# ──────────────────────────────────────────────
# _get_status
# ──────────────────────────────────────────────
class TestGetStatus:
    @pytest.mark.asyncio
    async def test_returns_payment_status(self, service):
        """Возвращает _status из объекта платежа."""
        mock_payment = MagicMock()
        mock_payment._status = "waiting_for_capture"

        with patch("payments.pay_config.asyncio.to_thread", new=AsyncMock(return_value=mock_payment)):
            result = await service._get_status("pay_123")

        assert result == "waiting_for_capture"

    @pytest.mark.asyncio
    async def test_none_payment_returns_none(self, service):
        """Payment.find_one вернул None → возвращает None."""
        with patch("payments.pay_config.asyncio.to_thread", new=AsyncMock(return_value=None)):
            result = await service._get_status("pay_missing")

        assert result is None

    @pytest.mark.asyncio
    async def test_exception_returns_none(self, service):
        """Исключение при find_one → возвращает None."""
        with patch(
            "payments.pay_config.asyncio.to_thread",
            new=AsyncMock(side_effect=Exception("timeout")),
        ):
            result = await service._get_status("pay_err")

        assert result is None
