"""
Tests for AdminStatsGetter.

AdminStatsGetter.get_data() calculates via BackendAPIClient:
- Total users
- Registrations: current week (Mon–Sun), month, year
- Churn: users whose ALL keys expired in period and have no active keys
- Blocked: users with is_blocked == True
"""

from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock

import pytest

from dialogs.windows.getters.admin.panel import AdminStatsGetter


def make_key_dict(
    email: str, tg_id: int, expiry_offset_ms: int, tariff_id: int = 20
) -> dict:
    """Build a backend-shaped dict for a Key with expiry_time relative to now.

    Args:
        email: Key email identifier.
        tg_id: Owner Telegram ID.
        expiry_offset_ms: Milliseconds from now; negative = already expired.
        tariff_id: Tariff ID.
    """
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    return {
        "tg_id": tg_id,
        "client_id": "c1",
        "email": email,
        "key": "k",
        "inbound_id": 1,
        "expiry_time": now_ms + expiry_offset_ms,
        "tariff_id": tariff_id,
    }


def make_user_dict(
    tg_id: int,
    username: str = "user",
    created_at: datetime = None,
    is_blocked: bool = False,
) -> dict:
    """Build a backend-shaped dict for a User."""
    return {
        "tg_id": tg_id,
        "username": f"{username}_{tg_id}",
        "trial": 0,
        "created_at": (created_at or datetime.now(timezone.utc)).isoformat(),
        "server_id": 1,
        "is_blocked": is_blocked,
    }


@pytest.fixture
def mock_dialog_manager():
    """Mock DialogManager with writable dialog_data."""
    manager = AsyncMock()
    manager.dialog_data = {}
    manager.start_data = {}
    manager.middleware_data = {}
    return manager


@pytest.fixture
def mock_backend():
    """Mock BackendAPIClient: admin_list_users + admin_list_keys."""
    backend = AsyncMock()
    backend.admin_list_users = AsyncMock(return_value=[])
    backend.admin_list_keys = AsyncMock(return_value=[])
    return backend


# ---------------------------------------------------------------------------
# AdminStatsGetter — структура результата
# ---------------------------------------------------------------------------


class TestAdminStatsGetterResultStructure:
    """Verify the shape of the dict returned by get_data()."""

    async def test_returns_stats_msg_key(
        self, mock_backend, mock_dialog_manager
    ):
        """get_data() must include 'STATS_MSG' key."""
        mock_backend.admin_list_users.return_value = []
        mock_backend.admin_list_keys.return_value = []

        getter = AdminStatsGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert "STATS_MSG" in result

    async def test_stores_all_keys_in_dialog_data(
        self, mock_backend, mock_dialog_manager
    ):
        """get_data() must store all_keys (as Key list) in dialog_data for handlers."""
        keys = [make_key_dict("a@b.com", 111, 10 * 24 * 3600 * 1000)]
        mock_backend.admin_list_users.return_value = []
        mock_backend.admin_list_keys.return_value = keys

        getter = AdminStatsGetter(mock_backend)
        await getter.get_data(mock_dialog_manager)

        assert "all_keys" in mock_dialog_manager.dialog_data
        assert len(mock_dialog_manager.dialog_data["all_keys"]) == 1

    async def test_exception_returns_error_message(
        self, mock_backend, mock_dialog_manager
    ):
        """When admin_list_users() raises, get_data() returns error dict (no crash)."""
        mock_backend.admin_list_users.side_effect = RuntimeError("Backend offline")

        getter = AdminStatsGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert "STATS_MSG" in result
        assert "Ошибка" in result["STATS_MSG"]


# ---------------------------------------------------------------------------
# AdminStatsGetter — общее количество пользователей
# ---------------------------------------------------------------------------


class TestAdminStatsGetterTotalUsers:
    """Verify total user count."""

    async def test_zero_users(self, mock_backend, mock_dialog_manager):
        """Empty user list should show 0 total."""
        mock_backend.admin_list_users.return_value = []
        mock_backend.admin_list_keys.return_value = []

        getter = AdminStatsGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert "Всего: 0" in result["STATS_MSG"]

    async def test_counts_users(self, mock_backend, mock_dialog_manager):
        """Total users must reflect actual count."""
        users = [make_user_dict(1), make_user_dict(2), make_user_dict(3)]
        mock_backend.admin_list_users.return_value = users
        mock_backend.admin_list_keys.return_value = []

        getter = AdminStatsGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert "Всего: 3" in result["STATS_MSG"]


# ---------------------------------------------------------------------------
# AdminStatsGetter — регистрации
# ---------------------------------------------------------------------------


class TestAdminStatsGetterRegistrations:
    """Verify registration counts for week, month, year."""

    async def test_new_user_this_week(self, mock_backend, mock_dialog_manager):
        """User registered this week should count in reg_week."""
        now = datetime.now(timezone.utc)
        users = [make_user_dict(1, created_at=now - timedelta(days=1))]
        mock_backend.admin_list_users.return_value = users
        mock_backend.admin_list_keys.return_value = []

        getter = AdminStatsGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert "Новые за неделю: 1" in result["STATS_MSG"]

    async def test_old_user_not_counted_this_week(
        self, mock_backend, mock_dialog_manager
    ):
        """User registered before this week should not count in reg_week."""
        now = datetime.now(timezone.utc)
        monday = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(
            days=now.weekday() + 7
        )
        users = [make_user_dict(1, created_at=monday)]
        mock_backend.admin_list_users.return_value = users
        mock_backend.admin_list_keys.return_value = []

        getter = AdminStatsGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert "Новые за неделю: 0" in result["STATS_MSG"]

    async def test_registrations_month(self, mock_backend, mock_dialog_manager):
        """User registered this month should count in reg_month."""
        now = datetime.now(timezone.utc)
        users = [make_user_dict(1, created_at=now - timedelta(days=5))]
        mock_backend.admin_list_users.return_value = users
        mock_backend.admin_list_keys.return_value = []

        getter = AdminStatsGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert "Новые за месяц: 1" in result["STATS_MSG"]

    async def test_registrations_year(self, mock_backend, mock_dialog_manager):
        """User registered this year should count in reg_year."""
        now = datetime.now(timezone.utc)
        users = [make_user_dict(1, created_at=now - timedelta(days=30))]
        mock_backend.admin_list_users.return_value = users
        mock_backend.admin_list_keys.return_value = []

        getter = AdminStatsGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert "Новые за год: 1" in result["STATS_MSG"]


# ---------------------------------------------------------------------------
# AdminStatsGetter — отток
# ---------------------------------------------------------------------------


class TestAdminStatsGetterChurn:
    """Verify churn counts: all keys expired in period, no active keys."""

    async def test_churned_user_this_week(self, mock_backend, mock_dialog_manager):
        """User whose only key expired this week should count as churn."""
        now = datetime.now(timezone.utc)
        # Ключ истёк 12 часов назад — гарантированно в текущей неделе
        # (избегаем граничный случай воскресенье→понедельник в CI)
        key = make_key_dict(
            "churned@b.com", 1, -12 * 3600 * 1000, tariff_id=20
        )

        user = make_user_dict(1, created_at=now - timedelta(days=30))

        mock_backend.admin_list_users.return_value = [user]
        mock_backend.admin_list_keys.return_value = [key]

        getter = AdminStatsGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert "Отток за неделю: 1" in result["STATS_MSG"]

    async def test_active_user_not_churned(self, mock_backend, mock_dialog_manager):
        """User with active key should NOT count as churn."""
        now = datetime.now(timezone.utc)
        monday = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(
            days=now.weekday()
        )

        user = make_user_dict(1, created_at=monday - timedelta(days=30))
        key = make_key_dict("active@b.com", 1, 10 * 24 * 3600 * 1000)  # expires in 10 days

        mock_backend.admin_list_users.return_value = [user]
        mock_backend.admin_list_keys.return_value = [key]

        getter = AdminStatsGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert "Отток за неделю: 0" in result["STATS_MSG"]

    async def test_user_without_keys_not_churned(
        self, mock_backend, mock_dialog_manager
    ):
        """User with no keys should NOT count as churn."""
        now = datetime.now(timezone.utc)
        user = make_user_dict(1, created_at=now - timedelta(days=30))

        mock_backend.admin_list_users.return_value = [user]
        mock_backend.admin_list_keys.return_value = []

        getter = AdminStatsGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert "Отток за неделю: 0" in result["STATS_MSG"]

    async def test_churn_month(self, mock_backend, mock_dialog_manager):
        """User whose key expired this month should count in churn_month."""
        now = datetime.now(timezone.utc)
        user = make_user_dict(1, created_at=now - timedelta(days=60))
        key = make_key_dict("churned@b.com", 1, -5 * 24 * 3600 * 1000)  # 5 days ago

        mock_backend.admin_list_users.return_value = [user]
        mock_backend.admin_list_keys.return_value = [key]

        getter = AdminStatsGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert "Отток за месяц: 1" in result["STATS_MSG"]

    async def test_churn_year(self, mock_backend, mock_dialog_manager):
        """User whose key expired this year should count in churn_year."""
        now = datetime.now(timezone.utc)
        user = make_user_dict(1, created_at=now - timedelta(days=400))
        key = make_key_dict("churned@b.com", 1, -30 * 24 * 3600 * 1000)  # 30 days ago

        mock_backend.admin_list_users.return_value = [user]
        mock_backend.admin_list_keys.return_value = [key]

        getter = AdminStatsGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert "Отток за год: 1" in result["STATS_MSG"]


# ---------------------------------------------------------------------------
# AdminStatsGetter — заблокированные
# ---------------------------------------------------------------------------


class TestAdminStatsGetterBlocked:
    """Verify blocked user count."""

    async def test_no_blocked(self, mock_backend, mock_dialog_manager):
        """When no users are blocked, count should be 0."""
        users = [make_user_dict(1), make_user_dict(2)]
        mock_backend.admin_list_users.return_value = users
        mock_backend.admin_list_keys.return_value = []

        getter = AdminStatsGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert "Заблокировали бота: 0" in result["STATS_MSG"]

    async def test_counts_blocked(self, mock_backend, mock_dialog_manager):
        """Blocked users must be counted correctly."""
        users = [
            make_user_dict(1),
            make_user_dict(2, is_blocked=True),
            make_user_dict(3, is_blocked=True),
        ]
        mock_backend.admin_list_users.return_value = users
        mock_backend.admin_list_keys.return_value = []

        getter = AdminStatsGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert "Заблокировали бота: 2" in result["STATS_MSG"]
