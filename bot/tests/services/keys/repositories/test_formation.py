from unittest.mock import patch, AsyncMock
import pytest
from services.core.keys.utils.calculator import ExpiryCalculator
from logger import logger


class TestFormationKey:
    @pytest.mark.asyncio
    async def test_generate_email(self, mock_cache, formation_key, key):
        formation_key.cache = mock_cache
        mock_cache.keys = AsyncMock()
        mock_cache.keys.all = AsyncMock(return_value=[key])
        email = await formation_key._generate_email()
        assert email not in [k.email for k in [key]]

    @pytest.mark.asyncio
    async def test_form_new_key(
        self, mock_cache, formation_key, key, server, inbound, tariff
    ):
        data_server = {
            "api_url": server.api_url,
            "login": server.login,
            "password": server.password,
            "inbound_id": inbound.inbound_id,
            "subscription_url": server.subscription_url,
        }
        with patch.object(
            formation_key.connected_data, "data", return_value=data_server
        ):
            result = await formation_key.form_new_key(
                tg_id=key.tg_id, tariff=tariff, server_id=1, number_of_months=1
            )

        calculator = ExpiryCalculator()
        expected_time_ms = calculator.key_duration_new_key(tariff.period, 1)

        from tests.conftest import convert_ms_to_date

        received_time = convert_ms_to_date(result.expiry_time)
        expected_time = convert_ms_to_date(expected_time_ms)
        assert received_time == expected_time
        assert result.inbound_id == inbound.inbound_id
        logger.debug(
            "Тест пройден успешно\n"
            f"Ожидаемое время: {expected_time}\n"
            f"Полученное время: {received_time}"
        )
