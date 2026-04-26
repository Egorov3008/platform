"""
Tests for KeySegmentationReportGetter.

This is NOT a DataGetter subclass — it has three independent async methods:
  - get_key_report()        — all keys summary
  - get_expiring_24h_details() — details for 24h expiring keys
  - get_expired_details()   — details for expired keys

All three read cache from dialog_manager.middleware_data["cache"].
KeyAdminReport is used live (pure Python, no I/O).
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from models import Key
from dialogs.windows.getters.admin.key_segmentation_report import (
    KeySegmentationReportGetter,
)


def make_key(email: str, tg_id: int, expiry_offset_ms: int) -> Key:
    """Build a Key with expiry relative to now.

    Negative offset = already expired.
    """
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    return Key(
        email=email,
        tg_id=tg_id,
        client_id="c1",
        key="k",
        inbound_id=1,
        expiry_time=now_ms + expiry_offset_ms,
    )


@pytest.fixture
def mock_dialog_manager():
    manager = AsyncMock()
    manager.dialog_data = {}
    manager.start_data = {}
    manager.middleware_data = {}
    return manager


def make_mock_cache(keys):
    """Build a mock CacheService where cache.keys.all() returns the given list."""
    cache = AsyncMock()
    cache.keys = AsyncMock()
    cache.keys.all = AsyncMock(return_value=keys)
    return cache


# ---------------------------------------------------------------------------
# get_key_report()
# ---------------------------------------------------------------------------


class TestKeySegmentationReportGetterKeyReport:
    """Tests for get_key_report() method."""

    async def test_returns_report_message_key(self, mock_dialog_manager):
        """get_key_report() must return 'report_message' key."""
        mock_dialog_manager.middleware_data["cache"] = make_mock_cache([])

        getter = KeySegmentationReportGetter()
        result = await getter.get_key_report(mock_dialog_manager)

        assert "report_message" in result

    async def test_returns_total_keys_key(self, mock_dialog_manager):
        """get_key_report() must return 'total_keys' key."""
        mock_dialog_manager.middleware_data["cache"] = make_mock_cache([])

        getter = KeySegmentationReportGetter()
        result = await getter.get_key_report(mock_dialog_manager)

        assert "total_keys" in result

    async def test_total_keys_matches_input(self, mock_dialog_manager):
        """total_keys must reflect the actual number of keys passed."""
        keys = [
            make_key("a@b.com", 1, 5 * 24 * 3600 * 1000),
            make_key("c@d.com", 2, -1000),
        ]
        mock_dialog_manager.middleware_data["cache"] = make_mock_cache(keys)

        getter = KeySegmentationReportGetter()
        result = await getter.get_key_report(mock_dialog_manager)

        assert result["total_keys"] == 2

    async def test_no_cache_returns_error(self, mock_dialog_manager):
        """When cache is absent from middleware_data, error dict is returned."""
        mock_dialog_manager.middleware_data = {}  # no cache

        getter = KeySegmentationReportGetter()
        result = await getter.get_key_report(mock_dialog_manager)

        assert result.get("error") is True
        assert "❌" in result["report_message"]

    async def test_empty_keys_list(self, mock_dialog_manager):
        """Empty key list must return valid report without error."""
        mock_dialog_manager.middleware_data["cache"] = make_mock_cache([])

        getter = KeySegmentationReportGetter()
        result = await getter.get_key_report(mock_dialog_manager)

        assert result.get("error") is False
        assert result["total_keys"] == 0

    async def test_exception_returns_error_dict(self, mock_dialog_manager):
        """When cache.keys.all() raises, get_key_report() returns error dict."""
        cache = AsyncMock()
        cache.keys = AsyncMock()
        cache.keys.all = AsyncMock(side_effect=RuntimeError("cache down"))
        mock_dialog_manager.middleware_data["cache"] = cache

        getter = KeySegmentationReportGetter()
        result = await getter.get_key_report(mock_dialog_manager)

        assert result.get("error") is True


# ---------------------------------------------------------------------------
# get_expiring_24h_details()
# ---------------------------------------------------------------------------


class TestKeySegmentationReportGetterExpiring24h:
    """Tests for get_expiring_24h_details() method."""

    async def test_returns_details_key(self, mock_dialog_manager):
        """get_expiring_24h_details() must return 'details' key."""
        mock_dialog_manager.middleware_data["cache"] = make_mock_cache([])

        getter = KeySegmentationReportGetter()
        result = await getter.get_expiring_24h_details(mock_dialog_manager)

        assert "details" in result

    async def test_no_expiring_keys_returns_no_error(self, mock_dialog_manager):
        """No 24h-expiring keys must return success result without error flag."""
        active = make_key("a@b.com", 1, 10 * 24 * 3600 * 1000)
        mock_dialog_manager.middleware_data["cache"] = make_mock_cache([active])

        getter = KeySegmentationReportGetter()
        result = await getter.get_expiring_24h_details(mock_dialog_manager)

        assert result.get("error") is False

    async def test_expiring_key_email_in_details(self, mock_dialog_manager):
        """Details string must mention the email of the expiring key."""
        expiring = make_key("soon@vpn.com", 1, 6 * 3600 * 1000)  # 6h from now
        mock_dialog_manager.middleware_data["cache"] = make_mock_cache([expiring])

        getter = KeySegmentationReportGetter()
        result = await getter.get_expiring_24h_details(mock_dialog_manager)

        assert "soon@vpn.com" in result["details"]

    async def test_no_cache_returns_error(self, mock_dialog_manager):
        """Absent cache must cause error return."""
        mock_dialog_manager.middleware_data = {}

        getter = KeySegmentationReportGetter()
        result = await getter.get_expiring_24h_details(mock_dialog_manager)

        assert "❌" in result["details"]


# ---------------------------------------------------------------------------
# get_expired_details()
# ---------------------------------------------------------------------------


class TestKeySegmentationReportGetterExpiredDetails:
    """Tests for get_expired_details() method."""

    async def test_returns_details_key(self, mock_dialog_manager):
        """get_expired_details() must return 'details' key."""
        mock_dialog_manager.middleware_data["cache"] = make_mock_cache([])

        getter = KeySegmentationReportGetter()
        result = await getter.get_expired_details(mock_dialog_manager)

        assert "details" in result

    async def test_expired_key_email_in_details(self, mock_dialog_manager):
        """Details string must mention the email of the expired key."""
        expired = make_key("dead@vpn.com", 2, -5 * 24 * 3600 * 1000)
        mock_dialog_manager.middleware_data["cache"] = make_mock_cache([expired])

        getter = KeySegmentationReportGetter()
        result = await getter.get_expired_details(mock_dialog_manager)

        assert "dead@vpn.com" in result["details"]

    async def test_no_cache_returns_error(self, mock_dialog_manager):
        """Absent cache must cause error return."""
        mock_dialog_manager.middleware_data = {}

        getter = KeySegmentationReportGetter()
        result = await getter.get_expired_details(mock_dialog_manager)

        assert "❌" in result["details"]
