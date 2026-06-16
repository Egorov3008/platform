"""
Tests for KeySegmentationReportGetter.

This is NOT a DataGetter subclass — it has three independent async methods:
  - get_key_report()        — all keys summary
  - get_expiring_24h_details() — details for 24h expiring keys
  - get_expired_details()   — details for expired keys

It pulls keys via ``backend_client.admin_list_keys()`` and feeds them into
``KeyAdminReport`` (pure Python, no I/O).
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from dialogs.windows.getters.admin.key_segmentation_report import (
    KeySegmentationReportGetter,
)


def make_key_dict(email: str, tg_id: int, expiry_offset_ms: int) -> dict:
    """Build a backend-shaped dict for a Key with expiry relative to now.

    Negative offset = already expired.
    """
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    return {
        "tg_id": tg_id,
        "client_id": "c1",
        "email": email,
        "expiry_time": now_ms + expiry_offset_ms,
        "key": "k",
        "inbound_id": 1,
        "tariff_id": 1,
    }


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
    return backend


# ---------------------------------------------------------------------------
# get_key_report()
# ---------------------------------------------------------------------------


class TestKeySegmentationReportGetterKeyReport:
    """Tests for get_key_report() method."""

    async def test_returns_report_message_key(self, mock_backend, mock_dialog_manager):
        """get_key_report() must return 'report_message' key."""
        mock_backend.admin_list_keys.return_value = []
        getter = KeySegmentationReportGetter(mock_backend)
        result = await getter.get_key_report(mock_dialog_manager)

        assert "report_message" in result

    async def test_returns_total_keys_key(self, mock_backend, mock_dialog_manager):
        """get_key_report() must return 'total_keys' key."""
        mock_backend.admin_list_keys.return_value = []
        getter = KeySegmentationReportGetter(mock_backend)
        result = await getter.get_key_report(mock_dialog_manager)

        assert "total_keys" in result

    async def test_total_keys_matches_input(self, mock_backend, mock_dialog_manager):
        """total_keys must reflect the actual number of keys passed."""
        keys = [
            make_key_dict("a@b.com", 1, 5 * 24 * 3600 * 1000),
            make_key_dict("c@d.com", 2, -1000),
        ]
        mock_backend.admin_list_keys.return_value = keys

        getter = KeySegmentationReportGetter(mock_backend)
        result = await getter.get_key_report(mock_dialog_manager)

        assert result["total_keys"] == 2

    async def test_empty_keys_list(self, mock_backend, mock_dialog_manager):
        """Empty key list must return valid report without error."""
        mock_backend.admin_list_keys.return_value = []

        getter = KeySegmentationReportGetter(mock_backend)
        result = await getter.get_key_report(mock_dialog_manager)

        assert result.get("error") is False
        assert result["total_keys"] == 0

    async def test_exception_returns_error_dict(
        self, mock_backend, mock_dialog_manager
    ):
        """When admin_list_keys() raises, get_key_report() returns error dict."""
        mock_backend.admin_list_keys.side_effect = RuntimeError("backend down")

        getter = KeySegmentationReportGetter(mock_backend)
        result = await getter.get_key_report(mock_dialog_manager)

        assert result.get("error") is True


# ---------------------------------------------------------------------------
# get_expiring_24h_details()
# ---------------------------------------------------------------------------


class TestKeySegmentationReportGetterExpiring24h:
    """Tests for get_expiring_24h_details() method."""

    async def test_returns_details_key(self, mock_backend, mock_dialog_manager):
        """get_expiring_24h_details() must return 'details' key."""
        mock_backend.admin_list_keys.return_value = []
        getter = KeySegmentationReportGetter(mock_backend)
        result = await getter.get_expiring_24h_details(mock_dialog_manager)

        assert "details" in result

    async def test_no_expiring_keys_returns_no_error(
        self, mock_backend, mock_dialog_manager
    ):
        """No 24h-expiring keys must return success result without error flag."""
        active = make_key_dict("a@b.com", 1, 10 * 24 * 3600 * 1000)
        mock_backend.admin_list_keys.return_value = [active]

        getter = KeySegmentationReportGetter(mock_backend)
        result = await getter.get_expiring_24h_details(mock_dialog_manager)

        assert result.get("error") is False

    async def test_expiring_key_email_in_details(
        self, mock_backend, mock_dialog_manager
    ):
        """Details string must mention the email of the expiring key."""
        expiring = make_key_dict("soon@vpn.com", 1, 6 * 3600 * 1000)  # 6h from now
        mock_backend.admin_list_keys.return_value = [expiring]

        getter = KeySegmentationReportGetter(mock_backend)
        result = await getter.get_expiring_24h_details(mock_dialog_manager)

        assert "soon@vpn.com" in result["details"]


# ---------------------------------------------------------------------------
# get_expired_details()
# ---------------------------------------------------------------------------


class TestKeySegmentationReportGetterExpiredDetails:
    """Tests for get_expired_details() method."""

    async def test_returns_details_key(self, mock_backend, mock_dialog_manager):
        """get_expired_details() must return 'details' key."""
        mock_backend.admin_list_keys.return_value = []
        getter = KeySegmentationReportGetter(mock_backend)
        result = await getter.get_expired_details(mock_dialog_manager)

        assert "details" in result

    async def test_expired_key_email_in_details(
        self, mock_backend, mock_dialog_manager
    ):
        """Details string must mention the email of the expired key."""
        expired = make_key_dict("dead@vpn.com", 2, -5 * 24 * 3600 * 1000)
        mock_backend.admin_list_keys.return_value = [expired]

        getter = KeySegmentationReportGetter(mock_backend)
        result = await getter.get_expired_details(mock_dialog_manager)

        assert "dead@vpn.com" in result["details"]
