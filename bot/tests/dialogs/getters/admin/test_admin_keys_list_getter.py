"""
Tests for AdminKeyListGetter and AdminKeyDetailsGetter.

AdminKeyListGetter.get_data():
- Reads 'current_segment' from dialog_data (default "all")
- Filters keys using live KeySegmentationService (not mocked — pure Python)
- Returns keys_message, keys_data, total_keys, segment

AdminKeyDetailsGetter.get_data():
- Reads 'selected_key' from start_data (email)
- Loads Key and Tariff from cache
- Uses KeyModel.to_dict() to return structured data
- Includes additional admin-specific fields
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from models import Key, Tariff
from dialogs.windows.getters.admin.keys_list import (
    AdminKeyListGetter,
    AdminKeyDetailsGetter,
)


def make_key(
    email: str,
    tg_id: int,
    expiry_offset_ms: int,
    total_gb: int = 10,
    tariff_id: int = 10,
) -> Key:
    """Build a Key with expiry relative to now.

    Negative expiry_offset_ms means the key has already expired.
    """
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    return Key(
        email=email,
        tg_id=tg_id,
        client_id="c1",
        key="k",
        inbound_id=1,
        expiry_time=now_ms + expiry_offset_ms,
        total_gb=total_gb,
        tariff_id=tariff_id,
    )


@pytest.fixture
def mock_dialog_manager():
    manager = AsyncMock()
    manager.dialog_data = {}
    manager.start_data = {}
    manager.middleware_data = {}
    return manager


@pytest.fixture
def mock_model_data():
    model_data = AsyncMock()
    model_data.keys = AsyncMock()
    return model_data


# ---------------------------------------------------------------------------
# AdminKeyListGetter
# ---------------------------------------------------------------------------


class TestAdminKeyListGetterResultStructure:
    """Result dict must always contain required keys."""

    async def test_returns_required_keys(self, mock_model_data, mock_dialog_manager):
        """get_data() must return keys_message, keys_data, total_keys, segment."""
        mock_model_data.keys.get_all.return_value = []

        getter = AdminKeyListGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)

        assert "keys_message" in result
        assert "keys_data" in result
        assert "total_keys" in result
        assert "segment" in result

    async def test_keys_data_is_list(self, mock_model_data, mock_dialog_manager):
        """keys_data must always be a list."""
        mock_model_data.keys.get_all.return_value = []

        getter = AdminKeyListGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)

        assert isinstance(result["keys_data"], list)

    async def test_total_keys_matches_keys_data_length(
        self, mock_model_data, mock_dialog_manager
    ):
        """total_keys must equal len(keys_data)."""
        keys = [
            make_key("a@b.com", 1, 5 * 24 * 3600 * 1000),
            make_key("c@d.com", 2, 8 * 24 * 3600 * 1000),
        ]
        mock_model_data.keys.get_all.return_value = keys

        getter = AdminKeyListGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)

        assert result["total_keys"] == len(result["keys_data"])


class TestAdminKeyListGetterDefaultSegment:
    """When no current_segment in dialog_data, default is 'all'."""

    async def test_default_segment_is_all(self, mock_model_data, mock_dialog_manager):
        """Absent current_segment defaults to 'all'."""
        keys = [make_key("a@b.com", 1, 5 * 24 * 3600 * 1000)]
        mock_model_data.keys.get_all.return_value = keys

        getter = AdminKeyListGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)

        assert result["segment"] == "all"

    async def test_all_segment_returns_all_keys(
        self, mock_model_data, mock_dialog_manager
    ):
        """With segment='all', all keys are returned regardless of status."""
        keys = [
            make_key("expired@b.com", 1, -1 * 24 * 3600 * 1000),
            make_key("active@b.com", 2, 10 * 24 * 3600 * 1000),
        ]
        mock_model_data.keys.get_all.return_value = keys

        getter = AdminKeyListGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)

        assert result["total_keys"] == 2


class TestAdminKeyListGetterSegmentFiltering:
    """Tests for segment-specific filtering via live KeySegmentationService."""

    async def test_expired_segment_excludes_active_keys(
        self, mock_model_data, mock_dialog_manager
    ):
        """Segment 'expired' must only return keys past their expiry."""
        mock_dialog_manager.dialog_data["current_segment"] = "expired"
        keys = [
            make_key("expired@b.com", 1, -1 * 24 * 3600 * 1000),
            make_key("active@b.com", 2, 10 * 24 * 3600 * 1000),
        ]
        mock_model_data.keys.get_all.return_value = keys

        getter = AdminKeyListGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)

        # All returned keys must be expired (expiry_time in the past)
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        for _, key in result["keys_data"]:
            assert key.expiry_time < now_ms

    async def test_expiring_24h_segment(self, mock_model_data, mock_dialog_manager):
        """Segment 'expiring_24h' must return keys expiring within 24 hours."""
        mock_dialog_manager.dialog_data["current_segment"] = "expiring_24h"
        expiring_soon = make_key("soon@b.com", 1, 12 * 3600 * 1000)  # 12 h from now
        far_future = make_key("far@b.com", 2, 10 * 24 * 3600 * 1000)  # 10 days
        already_expired = make_key("exp@b.com", 3, -1000)

        mock_model_data.keys.get_all.return_value = [
            expiring_soon,
            far_future,
            already_expired,
        ]

        getter = AdminKeyListGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)

        assert result["total_keys"] == 1
        assert result["keys_data"][0][1].email == "soon@b.com"

    async def test_keys_data_format_is_tuple_label_key(
        self, mock_model_data, mock_dialog_manager
    ):
        """Each entry in keys_data must be a (str, Key) tuple."""
        keys = [make_key("x@y.com", 99, 5 * 24 * 3600 * 1000)]
        mock_model_data.keys.get_all.return_value = keys

        getter = AdminKeyListGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)

        assert len(result["keys_data"]) == 1
        label, key = result["keys_data"][0]
        assert isinstance(label, str)
        assert isinstance(key, Key)

    async def test_label_contains_email_and_tg_id(
        self, mock_model_data, mock_dialog_manager
    ):
        """The label in keys_data must include email and tg_id."""
        keys = [make_key("info@vpn.ru", 12345, 5 * 24 * 3600 * 1000)]
        mock_model_data.keys.get_all.return_value = keys

        getter = AdminKeyListGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)

        label, _ = result["keys_data"][0]
        assert "info@vpn.ru" in label
        assert "12345" in label

    async def test_dialog_data_filtered_keys_stored(
        self, mock_model_data, mock_dialog_manager
    ):
        """get_data() must store filtered_keys in dialog_data."""
        keys = [make_key("a@b.com", 1, 5 * 24 * 3600 * 1000)]
        mock_model_data.keys.get_all.return_value = keys

        getter = AdminKeyListGetter(mock_model_data)
        await getter.get_data(mock_dialog_manager)

        assert "filtered_keys" in mock_dialog_manager.dialog_data

    async def test_unknown_segment_returns_empty(
        self, mock_model_data, mock_dialog_manager
    ):
        """An unknown segment name must return empty keys_data (no crash)."""
        mock_dialog_manager.dialog_data["current_segment"] = "unknown_segment"
        keys = [make_key("a@b.com", 1, 5 * 24 * 3600 * 1000)]
        mock_model_data.keys.get_all.return_value = keys

        getter = AdminKeyListGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)

        assert result["total_keys"] == 0
        assert result["keys_data"] == []


class TestAdminKeyListGetterExceptionHandling:
    """Error path returns graceful fallback dict."""

    async def test_exception_returns_error_dict(
        self, mock_model_data, mock_dialog_manager
    ):
        """When keys.get_all() raises, result must contain 'Ошибка'."""
        mock_model_data.keys.get_all.side_effect = RuntimeError("boom")

        getter = AdminKeyListGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)

        assert "keys_message" in result
        assert "Ошибка" in result["keys_message"]
        assert result["keys_data"] == []
        assert result["total_keys"] == 0


# ---------------------------------------------------------------------------
# AdminKeyDetailsGetter
# ---------------------------------------------------------------------------


class TestAdminKeyDetailsGetterResultShape:
    """Result dict structure for new KeyModel-based implementation."""

    async def test_missing_key_returns_error(self, mock_dialog_manager):
        """When email is not in start_data, returns error=True."""
        mock_dialog_manager.start_data = {}
        mock_dialog_manager.middleware_data = {"cache": AsyncMock()}

        getter = AdminKeyDetailsGetter()
        result = await getter.get_data(mock_dialog_manager)

        assert result.get("error") is True

    async def test_returns_keymodel_fields(self, mock_dialog_manager):
        """Returns all fields from KeyModel.to_dict()."""
        key = make_key("user@example.com", 123456, 10 * 24 * 3600 * 1000, total_gb=5)
        tariff = Tariff(id=10, name_tariff="Trial")

        cache_service = AsyncMock()
        cache_service.keys.get.return_value = key
        cache_service.tariffs.get.return_value = tariff
        mock_dialog_manager.middleware_data = {"cache": cache_service}
        mock_dialog_manager.start_data = {"selected_key": key}

        getter = AdminKeyDetailsGetter()
        result = await getter.get_data(mock_dialog_manager)

        # KeyModel.to_dict() fields should be present
        assert result.get("error") is False
        assert "status_emoji" in result
        assert "status_text" in result
        assert "is_trial" in result
        assert "is_active" in result
        assert "total_gb" in result
        assert "used_traffic" in result

    async def test_includes_admin_fields(self, mock_dialog_manager):
        """Includes additional admin-specific fields."""
        key = make_key("admin@test.com", 999, 10 * 24 * 3600 * 1000, tariff_id=1)
        tariff = Tariff(id=1, name_tariff="Premium")

        cache_service = AsyncMock()
        cache_service.keys.get.return_value = key
        cache_service.tariffs.get.return_value = tariff
        mock_dialog_manager.middleware_data = {"cache": cache_service}
        mock_dialog_manager.start_data = {"selected_key": key}

        getter = AdminKeyDetailsGetter()
        result = await getter.get_data(mock_dialog_manager)

        # Additional admin fields
        assert result.get("tg_id") == 999
        assert result.get("client_id") == "c1"
        assert result.get("inbound_id") == 1

    async def test_returns_error_when_tariff_missing(self, mock_dialog_manager):
        """Returns error=True if tariff not found."""
        key = make_key("user@example.com", 123, 10 * 24 * 3600 * 1000, tariff_id=99)

        cache_service = AsyncMock()
        cache_service.keys.get.return_value = key
        cache_service.tariffs.get.return_value = None
        mock_dialog_manager.middleware_data = {"cache": cache_service}
        mock_dialog_manager.start_data = {"selected_key": "user@example.com"}

        getter = AdminKeyDetailsGetter()
        result = await getter.get_data(mock_dialog_manager)

        assert result.get("error") is True
