"""
Tests for KeyListGetter - key list display with dialog data persistence.

KeyListGetter.get_data() fetches user keys and stores email in dialog_data.
Side-effectful: requires mocking ServiceDataModel.keys.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from models import Key
from dialogs.windows.getters.keys.key_list import KeyListGetter


@pytest.fixture
def mock_dialog_manager():
    """Mock DialogManager"""
    manager = AsyncMock()
    manager.event = MagicMock()
    manager.event.from_user = MagicMock()
    manager.event.from_user.id = 123456789
    manager.dialog_data = {}
    return manager


@pytest.fixture
def mock_model_data():
    """Mock ServiceDataModel"""
    model_data = AsyncMock()
    model_data.keys = AsyncMock()
    return model_data


@pytest.fixture
def sample_keys():
    """Sample Keys for user"""
    return [
        Key(
            email="user1@example.com",
            inbound_id=12,
            client_id="client1",
            tg_id=123456789,
            key="key_data1",
            expiry_time=int(datetime.now().timestamp() * 1000),
            tariff_id=1,
        ),
        Key(
            email="user2@example.com",
            inbound_id=13,
            client_id="client2",
            tg_id=123456789,
            key="key_data2",
            expiry_time=int(datetime.now().timestamp() * 1000),
            tariff_id=2,
        ),
    ]


class TestKeyListGetterBasic:
    """Test KeyListGetter.get_data() basic functionality"""

    @pytest.mark.asyncio
    async def test_get_data_multiple_keys(
        self, mock_model_data, mock_dialog_manager, sample_keys
    ):
        """get_data() should return list of keys with emails"""
        mock_model_data.keys.get_by.return_value = sample_keys

        getter = KeyListGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)

        assert "msg" in result
        assert "key_data" in result
        assert len(result["key_data"]) == 2
        assert result["key_data"][0] == (0, "user1@example.com")
        assert result["key_data"][1] == (1, "user2@example.com")

    @pytest.mark.asyncio
    async def test_get_data_single_key_as_list(
        self, mock_model_data, mock_dialog_manager, sample_keys
    ):
        """get_data() should handle single key returned as list"""
        mock_model_data.keys.get_by.return_value = sample_keys[:1]

        getter = KeyListGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)

        assert len(result["key_data"]) == 1
        assert result["key_data"][0] == (0, "user1@example.com")

    @pytest.mark.asyncio
    async def test_get_data_single_key_not_list(
        self, mock_model_data, mock_dialog_manager, sample_keys
    ):
        """get_data() should handle single key not returned as list"""
        single_key = sample_keys[0]
        mock_model_data.keys.get_by.return_value = single_key

        getter = KeyListGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)

        assert len(result["key_data"]) == 1
        assert result["key_data"][0] == (0, "user1@example.com")

    @pytest.mark.asyncio
    async def test_get_data_no_keys(self, mock_model_data, mock_dialog_manager):
        """get_data() should handle user with no keys"""
        mock_model_data.keys.get_by.return_value = None

        getter = KeyListGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)

        assert result["key_data"] == []
        assert "❌ Ключи не найдены" in result["msg"]

    @pytest.mark.asyncio
    async def test_get_data_empty_list(self, mock_model_data, mock_dialog_manager):
        """get_data() should handle empty list of keys"""
        mock_model_data.keys.get_by.return_value = []

        getter = KeyListGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)

        assert result["key_data"] == []
        assert "❌ Ключи не найдены" in result["msg"]


class TestKeyListGetterDialogData:
    """Test KeyListGetter dialog_data persistence"""

    @pytest.mark.asyncio
    async def test_get_data_stores_emails_in_dialog_data(
        self, mock_model_data, mock_dialog_manager, sample_keys
    ):
        """get_data() should store emails in dialog_data with index as key"""
        mock_model_data.keys.get_by.return_value = sample_keys

        getter = KeyListGetter(mock_model_data)
        await getter.get_data(mock_dialog_manager)

        assert mock_dialog_manager.dialog_data["0"] == "user1@example.com"
        assert mock_dialog_manager.dialog_data["1"] == "user2@example.com"

    @pytest.mark.asyncio
    async def test_get_data_stores_single_key_in_dialog_data(
        self, mock_model_data, mock_dialog_manager, sample_keys
    ):
        """get_data() should store single key email in dialog_data"""
        single_key = sample_keys[0]
        mock_model_data.keys.get_by.return_value = single_key

        getter = KeyListGetter(mock_model_data)
        await getter.get_data(mock_dialog_manager)

        assert mock_dialog_manager.dialog_data["0"] == "user1@example.com"

    @pytest.mark.asyncio
    async def test_get_data_does_not_store_on_no_keys(
        self, mock_model_data, mock_dialog_manager
    ):
        """get_data() should not store anything in dialog_data when no keys"""
        mock_model_data.keys.get_by.return_value = None

        getter = KeyListGetter(mock_model_data)
        await getter.get_data(mock_dialog_manager)

        assert mock_dialog_manager.dialog_data == {}


class TestKeyListGetterMessages:
    """Test KeyListGetter message generation"""

    @pytest.mark.asyncio
    async def test_get_data_message_with_keys(
        self, mock_model_data, mock_dialog_manager, sample_keys
    ):
        """get_data() should return descriptive message when keys exist"""
        mock_model_data.keys.get_by.return_value = sample_keys

        getter = KeyListGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)

        msg = result["msg"]
        assert "🔑" in msg
        assert "Список" in msg
        assert "устройств" in msg

    @pytest.mark.asyncio
    async def test_get_data_message_no_keys(self, mock_model_data, mock_dialog_manager):
        """get_data() should return error message when no keys"""
        mock_model_data.keys.get_by.return_value = None

        getter = KeyListGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)

        assert result["msg"] == "❌ Ключи не найдены"

    @pytest.mark.asyncio
    async def test_get_data_message_is_html(
        self, mock_model_data, mock_dialog_manager, sample_keys
    ):
        """get_data() should use HTML formatting in message"""
        mock_model_data.keys.get_by.return_value = sample_keys

        getter = KeyListGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)

        msg = result["msg"]
        assert "<b>" in msg
        assert "</b>" in msg
        assert "<i>" in msg
        assert "</i>" in msg


class TestKeyListGetterIntegration:
    """Integration tests for KeyListGetter"""

    @pytest.mark.asyncio
    async def test_get_data_calls_get_by_with_tg_id(
        self, mock_model_data, mock_dialog_manager, sample_keys
    ):
        """get_data() should call get_by with correct tg_id"""
        mock_model_data.keys.get_by.return_value = sample_keys

        getter = KeyListGetter(mock_model_data)
        await getter.get_data(mock_dialog_manager)

        mock_model_data.keys.get_by.assert_called_once_with(tg_id=123456789)

    @pytest.mark.asyncio
    async def test_get_data_full_flow_with_multiple_keys(
        self, mock_model_data, mock_dialog_manager, sample_keys
    ):
        """get_data() should handle complete key list flow"""
        mock_model_data.keys.get_by.return_value = sample_keys

        getter = KeyListGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)

        # Verify all required fields
        assert "msg" in result
        assert "key_data" in result

        # Verify key data structure
        assert len(result["key_data"]) == 2
        for i, (index, email) in enumerate(result["key_data"]):
            assert index == i
            assert email == sample_keys[i].email

        # Verify dialog_data populated
        for i, key in enumerate(sample_keys):
            assert mock_dialog_manager.dialog_data[str(i)] == key.email
