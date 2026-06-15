"""
Tests for KeyDetailsGetter - key detail view with status and traffic info.

After the migration to BackendAPIClient, KeyDetailsGetter delegates key
fetching to ``BackendAPIClient.get_key_details()`` (returns a dict shaped
like backend ``KeyDetailResponse``). This test suite mocks that single
async method and asserts the getter formats the dict into the dialog data
that the bot's key-details window expects.

Fields expected by the dialog window (from key_details.py):
    error, not_error, keys, tariff_name, used_traffic, total_gb,
    progress_bar, usage_percent, expiry_date, status_emoji, status_text,
    time_left_message, is_trial, not_trial_tariff, is_active,
    days_left, hours_left.
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from dialogs.windows.getters.keys.key_details import KeyDetailsGetter


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _key_details(
    *,
    email: str = "test@example.com",
    key: str = "vpn_key_data",
    tariff_id: int = 1,
    name_tariff: str | None = "Premium",
    total_gb_bytes: int = 10 * (1024**3),  # 10 GiB
    used_traffic_bytes: float = 1 * (1024**3),  # 1 GiB
    days_left: int = 30,
    hours_left: int = 0,
    is_active: bool = True,
    is_trial: bool = False,
    status_text: str = "Активна",
    expiry_date: str = "15 июля 2026 года",
) -> dict:
    """Build a dict shaped like backend KeyDetailResponse."""
    return {
        "email": email,
        "tg_id": 123456789,
        "client_id": "client-1",
        "expiry_time": int((datetime.utcnow() + timedelta(days=days_left)).timestamp() * 1000),
        "key": key,
        "tariff_id": tariff_id,
        "name_tariff": name_tariff,
        "total_gb": total_gb_bytes,
        "used_traffic": used_traffic_bytes,
        "inbound_id": 12,
        "public_link": key,
        "link_to_connect": key,
        "notified_10h": False,
        "notified_24h": False,
        "status_text": status_text,
        "days_left": days_left,
        "hours_left": hours_left,
        "is_active": is_active,
        "is_trial": is_trial,
        "expiry_date": expiry_date,
    }


@pytest.fixture
def mock_dialog_manager():
    """Mock DialogManager with email set in dialog_data."""
    manager = AsyncMock()
    manager.dialog_data = {"email": "test@example.com"}
    return manager


@pytest.fixture
def mock_backend_client():
    """Standalone AsyncMock for BackendAPIClient (avoids pulling conftest chain)."""
    return AsyncMock()


@pytest.fixture
def getter(mock_backend_client):
    return KeyDetailsGetter(backend_client=mock_backend_client)


# ---------------------------------------------------------------------------
# Basic flow
# ---------------------------------------------------------------------------


class TestKeyDetailsGetterBasic:
    @pytest.mark.asyncio
    async def test_get_data_key_found(self, getter, mock_backend_client, mock_dialog_manager):
        """get_data() should return formatted details when backend returns a key."""
        mock_backend_client.get_key_details.return_value = _key_details()

        result = await getter.get_data(mock_dialog_manager)

        mock_backend_client.get_key_details.assert_awaited_once_with("test@example.com")
        assert result["error"] is False
        assert result["not_error"] is True
        assert result["keys"] == "vpn_key_data"
        assert result["tariff_name"] == "Premium"
        # 1 GiB / 10 GiB = 10% = 1 of 10 filled
        assert result["used_traffic"] == 1.0
        assert result["total_gb"] == 10.0
        assert result["usage_percent"] == 10.0
        assert "█" in result["progress_bar"] or "░" in result["progress_bar"]

    @pytest.mark.asyncio
    async def test_get_data_key_not_found(
        self, getter, mock_backend_client, mock_dialog_manager
    ):
        """get_data() should return an error dict when backend returns None."""
        mock_backend_client.get_key_details.return_value = None

        result = await getter.get_data(mock_dialog_manager)

        assert result["error"] is True
        assert result["not_error"] is False
        assert result["keys"] == ""
        assert "не найден" in result["error_message"].lower()

    @pytest.mark.asyncio
    async def test_get_data_no_email(self, getter, mock_backend_client):
        """get_data() should bail out early when dialog_data has no email."""
        manager = AsyncMock()
        manager.dialog_data = {}  # no "email" key

        result = await getter.get_data(manager)

        # backend is not touched
        mock_backend_client.get_key_details.assert_not_awaited()
        assert result["error"] is True
        assert "email" in result["error_message"].lower()


# ---------------------------------------------------------------------------
# Status mapping
# ---------------------------------------------------------------------------


class TestKeyDetailsGetterStatus:
    @pytest.mark.asyncio
    async def test_active_key_status(
        self, getter, mock_backend_client, mock_dialog_manager
    ):
        """Active key → green emoji, days_left message."""
        mock_backend_client.get_key_details.return_value = _key_details(
            is_active=True, days_left=5, hours_left=0, status_text="Активна"
        )

        result = await getter.get_data(mock_dialog_manager)

        assert result["is_active"] is True
        assert result["status_emoji"] == "🟢"
        assert result["status_text"] == "Активна"
        assert "5" in result["time_left_message"]
        assert "дней" in result["time_left_message"].lower()

    @pytest.mark.asyncio
    async def test_expired_key_status(
        self, getter, mock_backend_client, mock_dialog_manager
    ):
        """Expired key (is_active=False) → red emoji, zero hours."""
        mock_backend_client.get_key_details.return_value = _key_details(
            is_active=False, days_left=0, hours_left=0, status_text="Истекла"
        )

        result = await getter.get_data(mock_dialog_manager)

        assert result["is_active"] is False
        assert result["status_emoji"] == "🔴"
        assert "0" in result["time_left_message"]

    @pytest.mark.asyncio
    async def test_expiring_soon_key_status(
        self, getter, mock_backend_client, mock_dialog_manager
    ):
        """Same-day, hours_left > 0 → yellow emoji, hours message."""
        mock_backend_client.get_key_details.return_value = _key_details(
            is_active=True, days_left=0, hours_left=12, status_text="Заканчивается"
        )

        result = await getter.get_data(mock_dialog_manager)

        assert result["is_active"] is True
        assert result["status_emoji"] == "🟡"
        assert "12" in result["time_left_message"]
        assert "часов" in result["time_left_message"].lower()


# ---------------------------------------------------------------------------
# Tariff handling
# ---------------------------------------------------------------------------


class TestKeyDetailsGetterTariff:
    @pytest.mark.asyncio
    async def test_regular_tariff(
        self, getter, mock_backend_client, mock_dialog_manager
    ):
        """tariff_id != 10 → not a trial, show its name."""
        mock_backend_client.get_key_details.return_value = _key_details(
            tariff_id=1, name_tariff="Premium", is_trial=False
        )

        result = await getter.get_data(mock_dialog_manager)

        assert result["is_trial"] is False
        assert result["not_trial_tariff"] is True
        assert result["tariff_name"] == "Premium"

    @pytest.mark.asyncio
    async def test_trial_tariff(
        self, getter, mock_backend_client, mock_dialog_manager
    ):
        """tariff_id == 10 → trial flag, hide 'Продлить ключ' paid button."""
        mock_backend_client.get_key_details.return_value = _key_details(
            tariff_id=10, name_tariff="Trial", is_trial=True
        )

        result = await getter.get_data(mock_dialog_manager)

        assert result["is_trial"] is True
        assert result["not_trial_tariff"] is False
        assert result["tariff_name"] == "Trial"

    @pytest.mark.asyncio
    async def test_missing_tariff_name_falls_back(
        self, getter, mock_backend_client, mock_dialog_manager
    ):
        """None name_tariff → 'Не указан' fallback."""
        mock_backend_client.get_key_details.return_value = _key_details(name_tariff=None)

        result = await getter.get_data(mock_dialog_manager)

        assert result["tariff_name"] == "Не указан"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestKeyDetailsGetterEdgeCases:
    @pytest.mark.asyncio
    async def test_zero_total_gb_does_not_divide_by_zero(
        self, getter, mock_backend_client, mock_dialog_manager
    ):
        """total_gb = 0 → usage_percent = 0, no ZeroDivisionError."""
        mock_backend_client.get_key_details.return_value = _key_details(
            total_gb_bytes=0, used_traffic_bytes=0
        )

        result = await getter.get_data(mock_dialog_manager)

        assert result["usage_percent"] == 0
        assert result["total_gb"] == 0
        assert result["used_traffic"] == 0

    @pytest.mark.asyncio
    async def test_backend_exception_returns_error(
        self, getter, mock_backend_client, mock_dialog_manager
    ):
        """If backend raises, getter should NOT propagate — it has no
        try/except, so the exception bubbles up. This test pins the
        current behavior so we'll notice if we add error handling later.
        """
        mock_backend_client.get_key_details.side_effect = RuntimeError("boom")

        with pytest.raises(RuntimeError, match="boom"):
            await getter.get_data(mock_dialog_manager)


# ---------------------------------------------------------------------------
# Required fields contract
# ---------------------------------------------------------------------------


class TestKeyDetailsGetterContract:
    @pytest.mark.asyncio
    async def test_all_required_fields_present(
        self, getter, mock_backend_client, mock_dialog_manager
    ):
        """Smoke-check that every field the dialog window depends on is set."""
        mock_backend_client.get_key_details.return_value = _key_details()

        result = await getter.get_data(mock_dialog_manager)

        required = {
            "error", "not_error", "keys", "tariff_name",
            "used_traffic", "total_gb", "progress_bar", "usage_percent",
            "expiry_date", "status_emoji", "status_text",
            "time_left_message", "is_trial", "not_trial_tariff",
            "is_active", "days_left", "hours_left",
        }
        missing = required - set(result.keys())
        assert not missing, f"Missing fields: {missing}"
