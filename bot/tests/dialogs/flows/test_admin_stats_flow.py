"""
Flow contract tests for Admin user stats: AdminStatsGetter

Source: dialogs/windows/getters/admin/panel.py

Tests verify:
- AdminStatsGetter writes all_keys to dialog_data
- Stats message contains user metrics (total, registrations, churn, blocked)
- AdminStatsMessage renders {STATS_MSG}
"""

from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest


def make_user_dict(
    tg_id: int,
    username: str = "user",
    created_at: datetime = None,
    is_blocked: bool = False,
) -> dict:
    """Helper: build a backend-shaped User dict."""
    return {
        "tg_id": tg_id,
        "username": f"{username}_{tg_id}",
        "trial": 0,
        "created_at": (created_at or datetime.now(timezone.utc)).isoformat(),
        "server_id": 1,
        "is_blocked": is_blocked,
    }


def make_key_dict(
    email: str,
    tg_id: int = 1,
    expiry_offset_ms: int = 86400000,
) -> dict:
    """Helper: build a backend-shaped Key dict."""
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    return {
        "email": email,
        "tg_id": tg_id,
        "client_id": "c1",
        "key": "k",
        "inbound_id": 1,
        "expiry_time": now_ms + expiry_offset_ms,
        "tariff_id": 1,
    }


@pytest.fixture
def mock_dialog_manager():
    """Mock DialogManager with dialog_data and middleware_data."""
    manager = AsyncMock()
    manager.dialog_data = {}
    manager.start_data = {}
    manager.middleware_data = {}
    manager.switch_to = AsyncMock()
    return manager


@pytest.fixture
def mock_backend():
    """Mock BackendAPIClient."""
    backend = AsyncMock()
    backend.admin_list_users = AsyncMock(return_value=[])
    backend.admin_list_keys = AsyncMock(return_value=[])
    return backend


# ---------------------------------------------------------------------------
# AdminStatsGetter — пишет в dialog_data
# ---------------------------------------------------------------------------


class TestAdminStatsGetterWritesDialogData:
    """Tests that AdminStatsGetter writes all_keys to dialog_data."""

    async def test_writes_all_keys_to_dialog_data(
        self, mock_dialog_manager, mock_backend
    ):
        """AdminStatsGetter writes dialog_data['all_keys'] with all available keys."""
        from dialogs.windows.getters.admin.panel import AdminStatsGetter

        keys = [
            make_key_dict("user1@example.com"),
            make_key_dict("user2@example.com"),
        ]
        mock_backend.admin_list_users.return_value = []
        mock_backend.admin_list_keys.return_value = keys

        getter = AdminStatsGetter(mock_backend)
        await getter.get_data(mock_dialog_manager)

        assert "all_keys" in mock_dialog_manager.dialog_data
        assert len(mock_dialog_manager.dialog_data["all_keys"]) == 2

    async def test_stats_contains_user_metrics(
        self, mock_dialog_manager, mock_backend
    ):
        """STATS_MSG должен содержать все ключевые метрики."""
        from dialogs.windows.getters.admin.panel import AdminStatsGetter

        now = datetime.now(timezone.utc)
        users = [
            make_user_dict(1, created_at=now - timedelta(days=1)),
            make_user_dict(2, created_at=now - timedelta(days=5)),
            make_user_dict(3, created_at=now - timedelta(days=100), is_blocked=True),
        ]
        keys = [make_key_dict("key1@example.com", tg_id=1, expiry_offset_ms=10 * 86400000)]

        mock_backend.admin_list_users.return_value = users
        mock_backend.admin_list_keys.return_value = keys

        getter = AdminStatsGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        msg = result["STATS_MSG"]
        assert "Всего: 3" in msg
        assert "Новые за неделю:" in msg
        assert "Новые за месяц:" in msg
        assert "Новые за год:" in msg
        assert "Отток за неделю:" in msg
        assert "Отток за месяц:" in msg
        assert "Отток за год:" in msg
        assert "Заблокировали бота: 1" in msg


# ---------------------------------------------------------------------------
# AdminStatsMessage — рендеринг виджета
# ---------------------------------------------------------------------------


class TestAdminStatsMessageBuilder:
    """Tests for AdminStatsMessage rendering."""

    def test_build_returns_format_with_stats_msg(self):
        """AdminStatsMessage.build должен вернуть Format с {STATS_MSG}."""
        from dialogs.windows.widgets.message.admin.panel import AdminStatsMessage
        from aiogram_dialog.widgets.text import Format

        message = AdminStatsMessage()
        result = message.build()

        assert isinstance(result, Format)
        assert "{STATS_MSG}" in result.text
