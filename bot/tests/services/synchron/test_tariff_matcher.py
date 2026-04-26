from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from py3xui import Client

from models import Tariff
from services.synchron.tariff_matcher import TariffMatcher


@pytest.fixture
def mock_model_data_tariffs():
    model_data = AsyncMock()
    model_data.tariffs = AsyncMock()
    model_data.tariffs.get_all = AsyncMock(
        return_value=[
            Tariff(id=1, name_tariff="Безлимит", limit_ip=1, traffic_limit=0),
            Tariff(id=7, name_tariff="100GB", limit_ip=1, traffic_limit=100),
            Tariff(id=8, name_tariff="2 IP", limit_ip=2, traffic_limit=100),
            Tariff(id=9, name_tariff="4 IP", limit_ip=4, traffic_limit=200),
            Tariff(id=10, name_tariff="10GB", limit_ip=1, traffic_limit=10),
        ]
    )
    return model_data


@pytest.fixture
def matcher(mock_model_data_tariffs):
    return TariffMatcher(mock_model_data_tariffs)


@pytest.fixture
def client():
    c = MagicMock(spec=Client)
    c.email = "test@example.com"
    c.limit_ip = 1
    c.total_gb = 100 * (1024**3)
    c.inbound_id = 1
    return c


@pytest.mark.asyncio
async def test_special_inbound_rule(matcher, client):
    """inbound_id=6 и total_gb=0 -> tariff_id=1"""
    client.inbound_id = 6
    client.total_gb = 0
    result = await matcher.match(client)
    assert result == 1


@pytest.mark.asyncio
async def test_special_inbound_rule_none_traffic(matcher, client):
    """inbound_id=6 и total_gb=None -> tariff_id=1"""
    client.inbound_id = 6
    client.total_gb = None
    result = await matcher.match(client)
    assert result == 1


@pytest.mark.asyncio
async def test_exact_match_100gb(matcher, client):
    """1 IP, 100GB -> tariff_id=7"""
    client.limit_ip = 1
    client.total_gb = 100 * (1024**3)
    result = await matcher.match(client)
    assert result == 7


@pytest.mark.asyncio
async def test_exact_match_10gb(matcher, client):
    """1 IP, 10GB -> tariff_id=10"""
    client.limit_ip = 1
    client.total_gb = 10 * (1024**3)
    result = await matcher.match(client)
    assert result == 10


@pytest.mark.asyncio
async def test_exact_match_2ip(matcher, client):
    """2 IP, 100GB -> tariff_id=8"""
    client.limit_ip = 2
    client.total_gb = 100 * (1024**3)
    result = await matcher.match(client)
    assert result == 8


@pytest.mark.asyncio
async def test_exact_match_4ip(matcher, client):
    """4 IP, 200GB -> tariff_id=9"""
    client.limit_ip = 4
    client.total_gb = 200 * (1024**3)
    result = await matcher.match(client)
    assert result == 9


@pytest.mark.asyncio
async def test_fallback_to_limit_ip(matcher, client):
    """Нет точного совпадения по трафику, но совпадает limit_ip -> первый найденный"""
    client.limit_ip = 2
    client.total_gb = 50 * (1024**3)  # Нет тарифа с 2 IP и 50GB
    result = await matcher.match(client)
    assert result == 8  # Первый с limit_ip=2


@pytest.mark.asyncio
@patch("services.synchron.tariff_matcher.DEFAULT_PRICING_PLAN", "5")
async def test_fallback_to_default(matcher, client):
    """Нет совпадения ни по чему -> DEFAULT_PRICING_PLAN"""
    client.limit_ip = 99
    client.total_gb = 999 * (1024**3)
    result = await matcher.match(client)
    assert result == 5


@pytest.mark.asyncio
async def test_unlimited_traffic_match(matcher, client):
    """1 IP, безлимит (total_gb=0) -> tariff_id=1"""
    client.limit_ip = 1
    client.total_gb = 0
    client.inbound_id = 1  # Не специальный inbound
    result = await matcher.match(client)
    assert result == 1  # Тариф с limit_ip=1, traffic_limit=0
