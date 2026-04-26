from datetime import datetime, timedelta

import pytest

from logger import logger


class TestKeyRenewal:
    @pytest.mark.asyncio
    async def test_extension_key(
        self, renewal_key, key, server, tariff, mock_xui_session, mock_cache, mock_conn
    ):
        from tests.conftest import convert_ms_to_date

        mock_xui_session.extend_client_key.return_value = True
        mock_conn.execute.return_value = True
        mock_cache.set_key.return_value = True
        number_of_months = 1
        mock_time = convert_ms_to_date(key.expiry_time)

        result = await renewal_key.extension_key(
            key, mock_conn, server, tariff, number_of_months
        )

        expected_datetime = datetime.now() + timedelta(days=tariff.period)
        received_time = convert_ms_to_date(result.expiry_time)

        logger.debug(
            f"Время истечения ключа: {mock_time}\n"
            f"Ожидаемое время: {expected_datetime.strftime('%Y-%m-%d %H:%M')}\n"
            f"Полученное время: {received_time}"
        )

        assert received_time == expected_datetime.strftime("%Y-%m-%d %H:%M")
        assert result.key == key.key
        logger.info("Тест пройден")
