from unittest.mock import patch

import pytest


class TestCreateKey:
    @pytest.mark.asyncio
    async def test_create_key_success(
        self,
        mock_cache,
        mock_xui_session,
        key_data,
        expiry_calculator,
        key,
        create_key,
        tariff,
        mock_conn,
        server,
        cache_data,
    ):
        # Настраиваем мок кэша
        mock_cache.get.return_value = None

        data_tariff = {"number_of_months": 1, "tariff_id": 1}

        with patch.object(create_key.cache_data, "getting", return_value=data_tariff):
            with patch.object(create_key, "_get_days", return_value=30):
                with patch.object(
                    create_key.expiry,
                    "key_duration_new_key",
                    return_value=1234567890000,
                ):
                    with patch.object(
                        create_key.form, "form_new_key", return_value=key
                    ):
                        mock_cache.set_key.return_value = True
                        mock_conn.execute.return_value = None
                        mock_xui_session.add_client.return_value = True
                        result = await create_key.proces(
                            key.tg_id, tariff, server.id, mock_conn, number_of_months=1
                        )

                        # Проверяем результат
                        assert result is not None
                        assert result["public_link"] == key.key
                        assert result["days"] == 30
