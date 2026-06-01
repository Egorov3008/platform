"""
Общая конфигурация тестов и фикстуры.
"""

from datetime import datetime
from unittest.mock import AsyncMock

import asyncpg
import pytest

from models import Inbound, GiftLink, PaymentModel, User, Tariff, Key, Server


# Оставляем базовые фикстуры, от которых зависят другие
@pytest.fixture
def mock_cache():
    from services.cache.service import CacheService

    cache: CacheService = AsyncMock()
    return cache


@pytest.fixture
def mock_backend_client():
    """Shared mock for BackendAPIClient (AsyncMock).

    Pre-stubs the most-used methods so attribute access never explodes.
    Tests that need different return values can override individual methods
    after fixture injection (e.g. ``mock.register_from_invite.return_value = ...``).

    Note: NOT using ``spec=BackendAPIClient`` because some methods return
    ``dict`` (e.g. ``create_payment``) and tests rely on subscripting
    those return values (``result["confirmation_url"]``). With ``spec=``,
    ``AsyncMock`` produces a generic ``MagicMock`` for return values,
    which breaks subscripting. Using a plain ``AsyncMock`` preserves
    normal dict semantics.
    """
    from api.backend_client import BackendAPIClient

    client = AsyncMock()  # type: BackendAPIClient
    client.get_user = AsyncMock(return_value=None)
    client.get_user_keys = AsyncMock(return_value=[])
    client.get_key = AsyncMock(return_value=None)
    client.create_trial_key = AsyncMock(return_value=None)
    # create_payment returns a dict; pre-stub so subscripting works by default.
    client.create_payment = AsyncMock(
        return_value={
            "payment_id": "test_payment_001",
            "confirmation_url": "https://example.com/pay",
            "amount": 0.0,
        }
    )
    client.get_payment_status = AsyncMock(return_value=None)
    return client


@pytest.fixture
def mock_backend(mock_backend_client):
    """Alias for backward-compat with existing test files using ``mock_backend``."""
    return mock_backend_client


@pytest.fixture
def mock_conn():
    conn = AsyncMock(spec=asyncpg.Pool)
    return conn


@pytest.fixture
def data_service():
    from database.service import DataService

    service = AsyncMock(spec=DataService)
    service.keys = AsyncMock()
    service.users = AsyncMock()
    service.tariffs = AsyncMock()
    service.servers = AsyncMock()
    service.payments = AsyncMock()
    service.gift_links = AsyncMock()
    service.inbounds = AsyncMock()
    service.gifts = AsyncMock()
    return service


@pytest.fixture
def checker_user():
    from services.core.user.utils.checked_admin import CheckedUser

    service = CheckedUser()
    return service


@pytest.fixture
def mock_xui_session():
    xui = AsyncMock()
    return xui


@pytest.fixture
def form_connect(mock_cache, server_data):
    from services.core.connect_module.repositories.form_data import FormConnectionData

    form_connect = FormConnectionData(mock_cache, server_data)
    form_connect.cache = mock_cache
    return form_connect


@pytest.fixture
def expiry_calculator():
    from services.core.keys.utils.calculator import ExpiryCalculator

    return ExpiryCalculator()


@pytest.fixture
def trial_service(user_data):
    from services.core.user.utils.trial import TrialService

    service = AsyncMock(spec=TrialService)
    service.user_data = user_data
    return service


# Остальные фикстуры, не относящиеся к конкретным модулям
@pytest.fixture
async def tariff_data(mock_cache):
    from services.core.tariff.data import TariffData

    service = TariffData(mock_cache)
    service.cache = mock_cache
    return service


@pytest.fixture
def server_data():
    return AsyncMock()


@pytest.fixture
async def payment_data(mock_cache, data_service):
    from services.core.payment.data import PaymentData

    service = PaymentData(mock_cache, data_service)
    service.cache = mock_cache
    service.data_service = data_service
    return service


@pytest.fixture
def user_data():
    return AsyncMock()


@pytest.fixture
def key_data():
    return AsyncMock()


@pytest.fixture
def gift_data(mock_cache, data_service):
    from services.core.data.service import ServiceDataModel

    model_data = AsyncMock(spec=ServiceDataModel)
    model_data.gifts = AsyncMock()
    return model_data


@pytest.fixture
def checker_link(gift_data):
    from services.core.gift.repositories.checker import CheckerGiftLink

    service = CheckerGiftLink(gift_data)
    return service


@pytest.fixture
def user_data_service():
    return AsyncMock()


@pytest.fixture
def server():
    return Server(
        id=1,
        server_name="Test Server",
        api_url="https://test-api.com",
        login="test_login",
        password="",
        subscription_url="https://test-sub.com",
        cluster_name="test_cluster",
    )


@pytest.fixture
def inbound():
    return Inbound(inbound_id=12, name_inbound="test", server_id=1)


@pytest.fixture
def key():
    return Key(
        email="test@test.com",
        inbound_id=1,
        client_id="123",
        tg_id=123,
        key="test",
        expiry_time=int(datetime.now().timestamp() * 1000),
        tariff_id=1,
    )


@pytest.fixture
def tariff():
    return Tariff(
        id=1, name_tariff="Test Tariff", period=30, traffic_limit=10.0, limit_ip=2
    )


@pytest.fixture
def user():
    return User(
        tg_id=123, username="test", trial=0, created_at=datetime.now(), server_id=1
    )


@pytest.fixture
def payment():
    return PaymentModel(
        payment_id="test_payment_123",
        tg_id=123,
        amount=99.99,
        payment_type="crypto",
        status="success",
    )


@pytest.fixture
def gift_link():
    return GiftLink(sender_tg_id=123, tariff_id=1, token="gift_token_123")


@pytest.fixture
def inbound_full():
    return Inbound(server_id=1, inbound_id=12, name_inbound="test_inbound")


def convert_ms_to_date(expiry_time):
    """Конвертирует миллисекунды в дату"""
    date = datetime.fromtimestamp(expiry_time / 1000.0)
    return date.strftime("%Y-%m-%d %H:%M")


# Dialog testing fixtures
@pytest.fixture
def mock_dialog_manager():
    """Mock DialogManager for dialog tests"""
    from aiogram_dialog import DialogManager

    manager = AsyncMock(spec=DialogManager)
    manager.dialog_data = {}
    manager.middleware_data = {}
    manager.is_preview = False
    manager.event = AsyncMock()
    manager.event.from_user = AsyncMock()
    manager.event.from_user.id = 123456789
    return manager


@pytest.fixture
def all_window_configs():
    """ALL_WINDOW_CONFIGS from dialogs.windows"""
    from dialogs.windows import ALL_WINDOW_CONFIGS

    return ALL_WINDOW_CONFIGS


@pytest.fixture
def usage_rules_states():
    """All UsageRules states for dialog tests"""
    from states import UsageRules

    return [
        UsageRules.main,
        UsageRules.page1,
        UsageRules.page2,
        UsageRules.page3,
        UsageRules.page4,
        UsageRules.page5,
        UsageRules.page6,
        UsageRules.page7,
        UsageRules.page8,
        UsageRules.page9,
    ]
