"""
Tests for AdminKeyListGetter and AdminKeyDetailsGetter.

AdminKeyListGetter.get_data() fetches keys via backend.admin_list_keys(),
runs them through KeySegmentationService (pure Python), and returns the
filtered list as (label, key) tuples.

AdminKeyDetailsGetter.get_data() reads `selected_key` from start_data, then
fetches the tariff via backend.get_tariff().

Source: dialogs/windows/getters/admin/keys_list.py
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from models import Key, Tariff
from dialogs.windows.getters.admin.keys_list import (
    AdminKeyListGetter,
    AdminKeyDetailsGetter,
)


def make_key_dict(
    email: str,
    tg_id: int,
    expiry_offset_ms: int,
    total_gb: int = 10,
    tariff_id: int = 10,
) -> dict:
    """Build a backend-shaped dict for a Key with expiry relative to now.

    Negative expiry_offset_ms means the key has already expired.
    """
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    return {
        "email": email,
        "tg_id": tg_id,
        "client_id": "c1",
        "key": "k",
        "inbound_id": 1,
        "expiry_time": now_ms + expiry_offset_ms,
        "total_gb": total_gb,
        "tariff_id": tariff_id,
    }


def make_key_obj(
    email: str,
    tg_id: int,
    expiry_offset_ms: int,
    total_gb: int = 10,
    tariff_id: int = 10,
) -> Key:
    """Build a Key dataclass with expiry relative to now."""
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
def mock_backend():
    backend = AsyncMock()
    backend.admin_list_keys = AsyncMock(return_value=[])
    backend.get_tariff = AsyncMock(return_value=None)
    return backend


# ---------------------------------------------------------------------------
# AdminKeyListGetter — структура результата
# ---------------------------------------------------------------------------


class TestAdminKeyListGetterResultStructure:
    """Result dict must always contain required keys."""

    async def test_returns_required_keys(self, mock_backend, mock_dialog_manager):
        """get_data() must return keys_message, keys_data, total_keys, segment."""
        mock_backend.admin_list_keys.return_value = []

        getter = AdminKeyListGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert "keys_message" in result
        assert "keys_data" in result
        assert "total_keys" in result
        assert "segment" in result

    async def test_keys_data_is_list(self, mock_backend, mock_dialog_manager):
        """keys_data must always be a list."""
        mock_backend.admin_list_keys.return_value = []

        getter = AdminKeyListGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert isinstance(result["keys_data"], list)

    async def test_total_keys_matches_keys_data_length(
        self, mock_backend, mock_dialog_manager
    ):
        """total_keys must equal len(keys_data)."""
        keys = [
            make_key_dict("a@b.com", 1, 5 * 24 * 3600 * 1000),
            make_key_dict("c@d.com", 2, 8 * 24 * 3600 * 1000),
        ]
        mock_backend.admin_list_keys.return_value = keys

        getter = AdminKeyListGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert result["total_keys"] == len(result["keys_data"])


# ---------------------------------------------------------------------------
# AdminKeyListGetter — сегмент по умолчанию
# ---------------------------------------------------------------------------


class TestAdminKeyListGetterDefaultSegment:
    """When no current_segment in dialog_data, default is 'all'."""

    async def test_default_segment_is_all(self, mock_backend, mock_dialog_manager):
        """Absent current_segment defaults to 'all'."""
        keys = [make_key_dict("a@b.com", 1, 5 * 24 * 3600 * 1000)]
        mock_backend.admin_list_keys.return_value = keys

        getter = AdminKeyListGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert result["segment"] == "all"

    async def test_all_segment_returns_all_keys(
        self, mock_backend, mock_dialog_manager
    ):
        """With segment='all', all keys are returned regardless of status."""
        keys = [
            make_key_dict("expired@b.com", 1, -1 * 24 * 3600 * 1000),
            make_key_dict("active@b.com", 2, 10 * 24 * 3600 * 1000),
        ]
        mock_backend.admin_list_keys.return_value = keys

        getter = AdminKeyListGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert result["total_keys"] == 2


# ---------------------------------------------------------------------------
# AdminKeyListGetter — сегментная фильтрация
# ---------------------------------------------------------------------------


class TestAdminKeyListGetterSegmentFiltering:
    """Tests for segment-specific filtering via live KeySegmentationService."""

    async def test_expired_segment_excludes_active_keys(
        self, mock_backend, mock_dialog_manager
    ):
        """Segment 'expired' must only return keys past their expiry."""
        mock_dialog_manager.dialog_data["current_segment"] = "expired"
        keys = [
            make_key_dict("expired@b.com", 1, -1 * 24 * 3600 * 1000),
            make_key_dict("active@b.com", 2, 10 * 24 * 3600 * 1000),
        ]
        mock_backend.admin_list_keys.return_value = keys

        getter = AdminKeyListGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        # All returned keys must be expired (expiry_time in the past)
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        for _, key in result["keys_data"]:
            assert key.expiry_time < now_ms

    async def test_expiring_24h_segment(self, mock_backend, mock_dialog_manager):
        """Segment 'expiring_24h' must return keys expiring within 24 hours."""
        mock_dialog_manager.dialog_data["current_segment"] = "expiring_24h"
        expiring_soon = make_key_dict("soon@b.com", 1, 12 * 3600 * 1000)  # 12 h from now
        far_future = make_key_dict("far@b.com", 2, 10 * 24 * 3600 * 1000)  # 10 days
        already_expired = make_key_dict("exp@b.com", 3, -1000)

        mock_backend.admin_list_keys.return_value = [
            expiring_soon,
            far_future,
            already_expired,
        ]

        getter = AdminKeyListGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert result["total_keys"] == 1
        assert result["keys_data"][0][1].email == "soon@b.com"

    async def test_keys_data_format_is_tuple_label_key(
        self, mock_backend, mock_dialog_manager
    ):
        """Each entry in keys_data must be a (str, Key) tuple."""
        keys = [make_key_dict("x@y.com", 99, 5 * 24 * 3600 * 1000)]
        mock_backend.admin_list_keys.return_value = keys

        getter = AdminKeyListGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert len(result["keys_data"]) == 1
        label, key = result["keys_data"][0]
        assert isinstance(label, str)
        assert isinstance(key, Key)

    async def test_label_contains_email_and_tg_id(
        self, mock_backend, mock_dialog_manager
    ):
        """The label in keys_data must include email and tg_id."""
        keys = [make_key_dict("info@vpn.ru", 12345, 5 * 24 * 3600 * 1000)]
        mock_backend.admin_list_keys.return_value = keys

        getter = AdminKeyListGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        label, _ = result["keys_data"][0]
        assert "info@vpn.ru" in label
        assert "12345" in label

    async def test_dialog_data_filtered_keys_stored(
        self, mock_backend, mock_dialog_manager
    ):
        """get_data() must store filtered_keys in dialog_data."""
        keys = [make_key_dict("a@b.com", 1, 5 * 24 * 3600 * 1000)]
        mock_backend.admin_list_keys.return_value = keys

        getter = AdminKeyListGetter(mock_backend)
        await getter.get_data(mock_dialog_manager)

        assert "filtered_keys" in mock_dialog_manager.dialog_data

    async def test_unknown_segment_returns_all(
        self, mock_backend, mock_dialog_manager
    ):
        """An unknown segment name falls through to filter_by_name → returns all keys.

        Documented behaviour: ``KeySegmentationService.filter_by_name`` returns
        the input list verbatim for unknown names (graceful fallback, no crash).
        """
        mock_dialog_manager.dialog_data["current_segment"] = "unknown_segment"
        keys = [make_key_dict("a@b.com", 1, 5 * 24 * 3600 * 1000)]
        mock_backend.admin_list_keys.return_value = keys

        getter = AdminKeyListGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert result["total_keys"] == 1
        assert len(result["keys_data"]) == 1


# ---------------------------------------------------------------------------
# AdminKeyListGetter — обработка ошибок
# ---------------------------------------------------------------------------


class TestAdminKeyListGetterExceptionHandling:
    """Error path returns graceful fallback dict."""

    async def test_exception_returns_error_dict(
        self, mock_backend, mock_dialog_manager
    ):
        """When admin_list_keys() raises, result must contain 'Ошибка'."""
        mock_backend.admin_list_keys.side_effect = RuntimeError("boom")

        getter = AdminKeyListGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert "keys_message" in result
        assert "Ошибка" in result["keys_message"]
        assert result["keys_data"] == []
        assert result["total_keys"] == 0


# ---------------------------------------------------------------------------
# AdminKeyDetailsGetter
# ---------------------------------------------------------------------------


def _make_tariff_dict(tariff_id: int = 10, name: str = "Trial") -> dict:
    return {
        "id": tariff_id,
        "name_tariff": name,
        "amount": 0.0,
        "period": 30,
        "traffic_limit": 0,
    }


class TestAdminKeyDetailsGetterResultShape:
    """Result dict structure for new KeyModel-based implementation."""

    async def test_missing_key_returns_error(
        self, mock_backend, mock_dialog_manager
    ):
        """When email is not in start_data, returns error=True."""
        mock_dialog_manager.start_data = {}

        getter = AdminKeyDetailsGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert result.get("error") is True

    async def test_returns_keymodel_fields(
        self, mock_backend, mock_dialog_manager
    ):
        """Returns all fields from KeyModel.to_dict()."""
        key = make_key_obj(
            "user@example.com", 123456, 10 * 24 * 3600 * 1000, total_gb=5
        )
        tariff = _make_tariff_dict(10, "Trial")

        mock_backend.get_tariff.return_value = tariff
        mock_dialog_manager.start_data = {"selected_key": key}

        getter = AdminKeyDetailsGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        # KeyModel.to_dict() fields should be present
        assert result.get("error") is False
        assert "status_emoji" in result
        assert "status_text" in result
        assert "is_trial" in result
        assert "is_active" in result
        assert "total_gb" in result
        assert "used_traffic" in result

    async def test_includes_admin_fields(
        self, mock_backend, mock_dialog_manager
    ):
        """Includes additional admin-specific fields."""
        key = make_key_obj(
            "admin@test.com", 999, 10 * 24 * 3600 * 1000, tariff_id=1
        )
        tariff = _make_tariff_dict(1, "Premium")

        mock_backend.get_tariff.return_value = tariff
        mock_dialog_manager.start_data = {"selected_key": key}

        getter = AdminKeyDetailsGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        # Additional admin fields
        assert result.get("tg_id") == 999
        assert result.get("client_id") == "c1"
        assert result.get("inbound_id") == 1

    async def test_returns_error_when_tariff_missing(
        self, mock_backend, mock_dialog_manager
    ):
        """Returns error=True if tariff not found."""
        key = make_key_obj(
            "user@example.com", 123, 10 * 24 * 3600 * 1000, tariff_id=99
        )

        mock_backend.get_tariff.return_value = None
        mock_dialog_manager.start_data = {"selected_key": key}

        getter = AdminKeyDetailsGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert result.get("error") is True
