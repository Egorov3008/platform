from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

from client import PanelClient


@pytest.fixture
async def mock_model_data():  # noqa: PT004
    """Фикстура для создания мока ServiceDataModel с зависимостями."""
    model_data = AsyncMock()
    model_data.users = AsyncMock()
    model_data.keys = AsyncMock()
    model_data.servers = AsyncMock()
    return model_data


@pytest.fixture
async def mock_xui_session():  # noqa: PT004
    """Фикстура для мока XUI сессии."""
    return AsyncMock()


@pytest.fixture
async def mock_pool():  # noqa: PT004
    """Фикстура для мока пула соединений с БД."""
    return AsyncMock()


@pytest.fixture
async def mock_http_session():  # noqa: PT004
    """Фикстура для мока aiohttp.ClientSession."""
    session = AsyncMock(spec=aiohttp.ClientSession)
    session.closed = False
    return session


@pytest.fixture
async def xui_fetcher():  # noqa: PT004
    """Фикстура для XUIFetcher."""
    from services.synchron.xui_fetcher import XUIFetcher

    return XUIFetcher()


@pytest.fixture
async def cache_comparator():  # noqa: PT004
    """Фикстура для CacheComparator."""
    from services.synchron.cache_comparator import CacheComparator

    return CacheComparator()


@pytest.fixture
async def mock_tariff_matcher():  # noqa: PT004
    """Фикстура для мока TariffMatcher."""
    matcher = AsyncMock()
    matcher.match = AsyncMock(return_value=10)
    return matcher


@pytest.fixture
async def key_creator(mock_model_data, mock_pool, mock_tariff_matcher):  # noqa: PT004
    """Фикстура для KeyCreator."""
    from services.synchron.key_creator import KeyCreator

    return KeyCreator(mock_model_data, mock_pool, mock_tariff_matcher)


@pytest.fixture
async def traffic_updater(mock_model_data):  # noqa: PT004
    """Фикстура для TrafficUpdater."""
    from services.synchron.traffic import TrafficUpdater

    return TrafficUpdater(mock_model_data)


@pytest.fixture
async def database_synchronizer(
    mock_model_data,
    mock_pool,
    xui_fetcher,
    cache_comparator,
    key_creator,
    traffic_updater,
):  # noqa: PT004
    """Фикстура для DatabaseSynchronizer."""
    from services.synchron.database_synchronizer import DatabaseSynchronizer

    return DatabaseSynchronizer(
        xui_fetcher=xui_fetcher,
        cache_comparator=cache_comparator,
        key_creator=key_creator,
        traffic_updater=traffic_updater,
        model_data=mock_model_data,
        pool=mock_pool,
    )


@pytest.fixture
async def sample_client():  # noqa: PT004
    """Фикстура для создания примера клиента PanelClient."""
    return PanelClient(
        id="client_123",
        email="test@example.com",
        tg_id=12345,
        inbound_id=1,
        sub_id="sub_123",
        expiry_time=1700000000000,
        total_gb=10 * (1024**3),
        limit_ip=1,
    )


@pytest.fixture
async def sample_key():  # noqa: PT004
    """Фикстура для создания примера ключа."""
    from models import Key

    return Key(
        email="test@example.com",
        client_id="client_123",
        inbound_id=1,
        tg_id=12345,
        key="subscription_link",
        expiry_time=1700000000000,
        tariff_id=10,
        total_gb=10 * (1024**3),
        used_traffic=0,
        limit_ip=1,
    )
