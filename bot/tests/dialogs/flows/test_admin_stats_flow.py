"""
Flow contract tests for Admin user stats: AdminStatsGetter

Tests verify:
- AdminStatsGetter writes all_keys to dialog_data
- Stats message contains user metrics (total, registrations, churn, blocked)
- AdminStatsMessage renders {STATS_MSG}
"""

from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from models import Key, User


def make_user(
    tg_id: int,
    username: str = "user",
    created_at: datetime = None,
    is_blocked: bool = False,
) -> User:
    """Helper to create a test User."""
    return User(
        tg_id=tg_id,
        username=f"{username}_{tg_id}",
        trial=0,
        created_at=created_at or datetime.now(timezone.utc),
        server_id=1,
        is_blocked=is_blocked,
    )


def make_key(
    email: str,
    tg_id: int = 1,
    expiry_offset_ms: int = 86400000,
) -> Key:
    """Helper to create a test Key."""
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
    """Mock DialogManager with dialog_data and middleware_data."""
    manager = AsyncMock()
    manager.dialog_data = {}
    manager.start_data = {}
    manager.middleware_data = {}
    manager.switch_to = AsyncMock()
    return manager


@pytest.fixture
def mock_model_data():
    """Mock ServiceDataModel."""
    model_data = AsyncMock()
    model_data.users = AsyncMock()
    model_data.keys = AsyncMock()
    return model_data


class TestAdminStatsGetterWritesDialogData:
    """Tests that AdminStatsGetter writes all_keys to dialog_data."""

    async def test_writes_all_keys_to_dialog_data(
        self, mock_dialog_manager, mock_model_data
    ):
        """AdminStatsGetter writes dialog_data['all_keys'] with all available keys."""
        from dialogs.windows.getters.admin.panel import AdminStatsGetter

        keys = [
            make_key("user1@example.com"),
            make_key("user2@example.com"),
        ]
        mock_model_data.users.get_all.return_value = []
        mock_model_data.keys.get_all.return_value = keys

        getter = AdminStatsGetter(mock_model_data)
        await getter.get_data(mock_dialog_manager)

        assert "all_keys" in mock_dialog_manager.dialog_data
        assert len(mock_dialog_manager.dialog_data["all_keys"]) == 2

    async def test_stats_contains_user_metrics(
        self, mock_dialog_manager, mock_model_data
    ):
        """STATS_MSG должен содержать все новые метрики."""
        from dialogs.windows.getters.admin.panel import AdminStatsGetter

        now = datetime.now(timezone.utc)
        users = [
            make_user(1, created_at=now - timedelta(days=1)),
            make_user(2, created_at=now - timedelta(days=5)),
            make_user(3, created_at=now - timedelta(days=100), is_blocked=True),
        ]
        keys = [make_key("key1@example.com", tg_id=1, expiry_offset_ms=10 * 86400000)]

        mock_model_data.users.get_all.return_value = users
        mock_model_data.keys.get_all.return_value = keys

        getter = AdminStatsGetter(mock_model_data)
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
