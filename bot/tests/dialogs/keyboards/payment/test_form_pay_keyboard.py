"""
Тесты для PaymentFormKeyboard (dialogs/windows/widgets/keybord/payment/form_pay.py).

Покрытие:
- build(): возвращает Column с 4 кнопками
- _paid_for(): happy path — payment_processor.route + callback.answer "✅"
- _paid_for(): нет payment_id — ни route, ни answer не вызываются
- _paid_for(): исключение в route — callback.answer с ошибкой "❌"

Стратегия:
- PaymentRouter и ServiceDataModel мокируются через AsyncMock/MagicMock
- callback и dialog_manager мокируются вручную
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram_dialog.widgets.kbd import Column

from dialogs.windows.widgets.keybord.payment.form_pay import PaymentFormKeyboard


# ──────────────────────────────────────────────
# Фикстуры
# ──────────────────────────────────────────────

@pytest.fixture
def mock_payment_router():
    """Мок PaymentRouter."""
    router = AsyncMock()
    router.route = AsyncMock()
    return router


@pytest.fixture
def mock_model_service():
    """Мок ServiceDataModel."""
    return MagicMock()


@pytest.fixture
def keyboard(mock_payment_router, mock_model_service):
    """PaymentFormKeyboard с мок-зависимостями."""
    return PaymentFormKeyboard(
        payment_processor=mock_payment_router,
        model_service=mock_model_service,
    )


@pytest.fixture
def mock_callback():
    """Мок CallbackQuery."""
    cb = AsyncMock()
    cb.answer = AsyncMock()
    return cb


@pytest.fixture
def mock_manager():
    """Мок DialogManager с dialog_data."""
    manager = AsyncMock()
    manager.dialog_data = {"payment_id": "pay_keyboard_001"}
    return manager


# ──────────────────────────────────────────────
# build()
# ──────────────────────────────────────────────

class TestBuild:
    def test_returns_column(self, keyboard):
        """build() возвращает Column-виджет."""
        widget = keyboard.build()
        assert isinstance(widget, Column)

    def test_column_has_four_children(self, keyboard):
        """Column содержит 4 дочерних виджета (в атрибуте .buttons)."""
        widget = keyboard.build()
        # aiogram-dialog Column хранит дочерние виджеты в .buttons
        assert hasattr(widget, "buttons")
        assert len(widget.buttons) == 4

    def test_build_called_multiple_times_returns_column(self, keyboard):
        """build() можно вызвать несколько раз — всегда возвращает Column."""
        for _ in range(3):
            assert isinstance(keyboard.build(), Column)


# ──────────────────────────────────────────────
# _paid_for()
# ──────────────────────────────────────────────

class TestPaidFor:
    @pytest.mark.asyncio
    async def test_happy_path_routes_payment(
        self, keyboard, mock_payment_router, mock_callback, mock_manager
    ):
        """Успешная проверка: вызывает route с payment_id."""
        await keyboard._paid_for(mock_callback, None, mock_manager)

        mock_payment_router.route.assert_awaited_once_with("pay_keyboard_001")

    @pytest.mark.asyncio
    async def test_happy_path_answers_ok(
        self, keyboard, mock_callback, mock_manager
    ):
        """После успешного route — отвечает '✅ Статус платежа проверен'."""
        await keyboard._paid_for(mock_callback, None, mock_manager)

        mock_callback.answer.assert_awaited_once_with(
            "✅ Статус платежа проверен", show_alert=False
        )

    @pytest.mark.asyncio
    async def test_no_payment_id_skips_route(
        self, keyboard, mock_payment_router, mock_callback, mock_manager
    ):
        """Если payment_id отсутствует — route не вызывается, но answer вызывается с ошибкой."""
        mock_manager.dialog_data = {}  # нет payment_id

        await keyboard._paid_for(mock_callback, None, mock_manager)

        mock_payment_router.route.assert_not_awaited()
        mock_callback.answer.assert_awaited_once_with(
            "⚠️ Платеж не найден", show_alert=True
        )

    @pytest.mark.asyncio
    async def test_route_exception_answers_error(
        self, keyboard, mock_payment_router, mock_callback, mock_manager
    ):
        """Если route бросает исключение — отвечает '❌ Ошибка при проверке платежа. Обратитесь в поддержку.'."""
        mock_payment_router.route.side_effect = RuntimeError("payment failed")

        await keyboard._paid_for(mock_callback, None, mock_manager)

        mock_callback.answer.assert_awaited_once_with(
            "❌ Ошибка при проверке платежа. Обратитесь в поддержку.", show_alert=True
        )

    @pytest.mark.asyncio
    async def test_route_exception_does_not_propagate(
        self, keyboard, mock_payment_router, mock_callback, mock_manager
    ):
        """Исключение в route поглощается — метод завершается без raise."""
        mock_payment_router.route.side_effect = ValueError("unexpected")

        # Не бросает исключение
        await keyboard._paid_for(mock_callback, None, mock_manager)

    @pytest.mark.asyncio
    async def test_payment_id_none_skips_route(
        self, keyboard, mock_payment_router, mock_callback, mock_manager
    ):
        """Явный None в payment_id — route не вызывается."""
        mock_manager.dialog_data = {"payment_id": None}

        await keyboard._paid_for(mock_callback, None, mock_manager)

        mock_payment_router.route.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_uses_payment_id_from_dialog_data(
        self, keyboard, mock_payment_router, mock_callback, mock_manager
    ):
        """payment_id берётся из dialog_manager.dialog_data."""
        mock_manager.dialog_data = {"payment_id": "custom_pay_xyz"}

        await keyboard._paid_for(mock_callback, None, mock_manager)

        mock_payment_router.route.assert_awaited_once_with("custom_pay_xyz")
