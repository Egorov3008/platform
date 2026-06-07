"""
Tests for KeyListGetter using BackendAPIClient.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from api.backend_client import BackendAPIClient
from api.schemas import KeyDTO
from dialogs.windows.getters.keys.key_list import KeyListGetter


@pytest.fixture
def mock_dialog_manager():
    manager = AsyncMock()
    manager.event = MagicMock()
    manager.event.from_user = MagicMock()
    manager.event.from_user.id = 123456789
    manager.dialog_data = {}
    return manager


@pytest.fixture
def sample_keys():
    return [
        KeyDTO(
            email="user1@example.com",
            tg_id=123456789,
            expiry_time=9999999999000,
            key="key_data1",
            inbound_id=12,
            tariff_id=1,
            client_id="abc-123",
            name_tariff="Test",
        ),
        KeyDTO(
            email="user2@example.com",
            tg_id=123456789,
            expiry_time=9999999999000,
            key="key_data2",
            inbound_id=13,
            tariff_id=1,
            client_id="def-456",
            name_tariff="Test",
        ),
    ]


class TestKeyListGetterBasic:

    @pytest.mark.asyncio
    async def test_get_data_multiple_keys(self, mock_backend, mock_dialog_manager, sample_keys):
        mock_backend.get_user_keys = AsyncMock(return_value=sample_keys)
        getter = KeyListGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert len(result["key_data"]) == 2
        assert result["key_data"][0] == (0, "user1@example.com")
        assert result["key_data"][1] == (1, "user2@example.com")

    @pytest.mark.asyncio
    async def test_get_data_no_keys(self, mock_backend, mock_dialog_manager):
        mock_backend.get_user_keys = AsyncMock(return_value=[])
        getter = KeyListGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert result["key_data"] == []
        assert "❌ Ключи не найдены" in result["msg"]

    @pytest.mark.asyncio
    async def test_get_data_calls_backend_with_tg_id(self, mock_backend, mock_dialog_manager, sample_keys):
        mock_backend.get_user_keys = AsyncMock(return_value=sample_keys)
        getter = KeyListGetter(mock_backend)
        await getter.get_data(mock_dialog_manager)

        mock_backend.get_user_keys.assert_called_once_with(123456789)


class TestKeyListGetterDialogData:

    @pytest.mark.asyncio
    async def test_stores_emails_in_dialog_data(self, mock_backend, mock_dialog_manager, sample_keys):
        mock_backend.get_user_keys = AsyncMock(return_value=sample_keys)
        getter = KeyListGetter(mock_backend)
        await getter.get_data(mock_dialog_manager)

        assert mock_dialog_manager.dialog_data["0"] == "user1@example.com"
        assert mock_dialog_manager.dialog_data["1"] == "user2@example.com"

    @pytest.mark.asyncio
    async def test_empty_dialog_data_on_no_keys(self, mock_backend, mock_dialog_manager):
        mock_backend.get_user_keys = AsyncMock(return_value=[])
        getter = KeyListGetter(mock_backend)
        await getter.get_data(mock_dialog_manager)

        assert mock_dialog_manager.dialog_data == {}


class TestKeyListGetterMessages:

    @pytest.mark.asyncio
    async def test_message_with_keys_has_html(self, mock_backend, mock_dialog_manager, sample_keys):
        mock_backend.get_user_keys = AsyncMock(return_value=sample_keys)
        getter = KeyListGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert "<b>" in result["msg"]
        assert "🔑" in result["msg"]

    @pytest.mark.asyncio
    async def test_error_fallback_on_exception(self, mock_backend, mock_dialog_manager):
        mock_backend.get_user_keys = AsyncMock(side_effect=Exception("network error"))
        getter = KeyListGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert result["key_data"] == []
        assert "Ошибка" in result["msg"]
