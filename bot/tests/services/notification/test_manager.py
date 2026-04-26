"""
Тесты для FunnelManager (services/notification/manager.py).

Проверяем:
- register() добавляет воронку
- run_cycle() пропускает цикл вне временного окна
- run_cycle() пропускает заблокированных пользователей
- run_cycle() вызывает should_send для каждого пользователя
- _get_segment_keys() возвращает [] для user-level воронок
- _get_segment_keys() вызывает KeySegmentationService для ключевых воронок
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import asyncpg

from models import User, Key
from services.cache.service import CacheService
from services.notification.manager import FunnelManager
from services.notification.models import NotificationResult
from services.notification.routing import KEY_SEGMENT_TO_FUNNEL


def make_user(tg_id: int = 123456, is_blocked: bool = False) -> User:
    return User(
        tg_id=tg_id,
        is_blocked=is_blocked,
        created_at=datetime.now() - timedelta(days=7),
    )


def make_key(email: str = "test@example.com", tg_id: int = 123456) -> Key:
    now_ms = int(datetime.now().timestamp() * 1000)
    return Key(
        tg_id=tg_id,
        email=email,
        client_id="cli_1",
        expiry_time=now_ms + 12 * 3600 * 1000,
        key="vless://...",
        inbound_id=1,
    )


def make_mock_funnel(funnel_id: str, should_send_result: bool = True) -> MagicMock:
    funnel = MagicMock()
    funnel.funnel_id = funnel_id
    funnel.should_send = AsyncMock(return_value=should_send_result)
    funnel.process = AsyncMock(
        return_value=NotificationResult(tg_id=123456, funnel_id=funnel_id, sent=1)
    )
    return funnel


@pytest.fixture
def mock_cache():
    cache = MagicMock(spec=CacheService)
    cache.users = AsyncMock()
    cache.keys = AsyncMock()
    cache.users.all = AsyncMock(return_value=[])
    cache.keys.all = AsyncMock(return_value=[])
    cache.storage = AsyncMock()
    return cache


@pytest.fixture
def mock_pool():
    return AsyncMock(spec=asyncpg.Pool)


@pytest.fixture
def manager(mock_cache, mock_pool) -> FunnelManager:
    return FunnelManager(mock_cache, mock_pool)


@pytest.fixture
def mock_bot():
    return MagicMock()


class TestFunnelManagerRegister:
    """Тесты для register()."""

    def test_register_adds_funnel(self, manager):
        funnel = make_mock_funnel("key_expiry_24h")
        manager.register(funnel)
        assert funnel in manager._funnels

    def test_register_multiple_funnels(self, manager):
        f1 = make_mock_funnel("f1")
        f2 = make_mock_funnel("f2")
        manager.register(f1)
        manager.register(f2)
        assert len(manager._funnels) == 2


class TestFunnelManagerInSendingWindow:
    """Тесты для _in_sending_window()."""

    def test_inside_window_returns_true(self):
        with patch("services.notification.manager.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2025, 12, 16, 14, 0, 0)
            result = FunnelManager._in_sending_window()
        assert result is True

    def test_before_window_returns_false(self):
        with patch("services.notification.manager.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2025, 12, 16, 7, 0, 0)
            result = FunnelManager._in_sending_window()
        assert result is False

    def test_after_window_returns_false(self):
        with patch("services.notification.manager.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2025, 12, 16, 23, 0, 0)
            result = FunnelManager._in_sending_window()
        assert result is False

    def test_at_start_of_window_returns_true(self):
        with patch("services.notification.manager.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2025, 12, 16, 9, 0, 0)
            result = FunnelManager._in_sending_window()
        assert result is True


class TestFunnelManagerRunCycle:
    """Тесты для run_cycle()."""

    async def test_skips_cycle_outside_window(self, manager, mock_bot):
        funnel = make_mock_funnel("f1")
        manager.register(funnel)
        with patch("services.notification.manager.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2025, 12, 16, 7, 0, 0)
            report = await manager.run_cycle(mock_bot)
        funnel.should_send.assert_not_called()
        assert report.total_users == 0
        assert report.results_by_funnel == {}

    async def test_skips_blocked_users(self, manager, mock_cache, mock_bot):
        blocked_user = make_user(tg_id=111, is_blocked=True)
        active_user = make_user(tg_id=222, is_blocked=False)
        mock_cache.users.all.return_value = [blocked_user, active_user]
        mock_cache.keys.all.return_value = []

        funnel = make_mock_funnel("cold_lead", should_send_result=False)
        manager.register(funnel)

        with patch("services.notification.manager.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2025, 12, 16, 12, 0, 0)
            await manager.run_cycle(mock_bot)

        # should_send должен вызываться только для active_user
        tg_ids_called = [
            call.args[0].user.tg_id for call in funnel.should_send.call_args_list
        ]
        assert 111 not in tg_ids_called
        assert 222 in tg_ids_called

    async def test_calls_should_send_for_each_user_and_funnel(
        self, manager, mock_cache, mock_bot
    ):
        users = [make_user(tg_id=i) for i in range(3)]
        mock_cache.users.all.return_value = users
        mock_cache.keys.all.return_value = []

        funnel = make_mock_funnel("cold_lead", should_send_result=False)
        manager.register(funnel)

        with patch("services.notification.manager.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2025, 12, 16, 12, 0, 0)
            await manager.run_cycle(mock_bot)

        assert funnel.should_send.call_count == 3

    async def test_calls_process_when_should_send_is_true(
        self, manager, mock_cache, mock_bot
    ):
        user = make_user()
        mock_cache.users.all.return_value = [user]
        mock_cache.keys.all.return_value = []

        funnel = make_mock_funnel("cold_lead", should_send_result=True)
        manager.register(funnel)

        with patch("services.notification.manager.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2025, 12, 16, 12, 0, 0)
            await manager.run_cycle(mock_bot)

        funnel.process.assert_called_once()

    async def test_does_not_call_process_when_should_send_is_false(
        self, manager, mock_cache, mock_bot
    ):
        user = make_user()
        mock_cache.users.all.return_value = [user]
        mock_cache.keys.all.return_value = []

        funnel = make_mock_funnel("cold_lead", should_send_result=False)
        manager.register(funnel)

        with patch("services.notification.manager.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2025, 12, 16, 12, 0, 0)
            await manager.run_cycle(mock_bot)

        funnel.process.assert_not_called()

    async def test_report_accumulates_results(self, manager, mock_cache, mock_bot):
        users = [make_user(tg_id=1), make_user(tg_id=2)]
        mock_cache.users.all.return_value = users
        mock_cache.keys.all.return_value = []

        funnel = MagicMock()
        funnel.funnel_id = "cold_lead"
        funnel.should_send = AsyncMock(return_value=True)
        funnel.process = AsyncMock(
            side_effect=[
                NotificationResult(tg_id=1, funnel_id="cold_lead", sent=1),
                NotificationResult(tg_id=2, funnel_id="cold_lead", sent=1),
            ]
        )
        manager.register(funnel)

        with patch("services.notification.manager.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2025, 12, 16, 12, 0, 0)
            report = await manager.run_cycle(mock_bot)

        assert report.results_by_funnel["cold_lead"]["sent"] == 2

    async def test_report_total_users_is_set(self, manager, mock_cache, mock_bot):
        users = [make_user(tg_id=i) for i in range(5)]
        mock_cache.users.all.return_value = users
        mock_cache.keys.all.return_value = []

        with patch("services.notification.manager.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2025, 12, 16, 12, 0, 0)
            report = await manager.run_cycle(mock_bot)

        assert report.total_users == 5


class TestGetSegmentKeys:
    """Тесты для _get_segment_keys()."""

    async def test_returns_empty_for_user_level_funnel(self, manager):
        """cold_lead не в KEY_SEGMENT_TO_FUNNEL → segment_keys = []."""
        assert "cold_lead" not in KEY_SEGMENT_TO_FUNNEL.values()
        keys = [make_key()]
        result = await manager._get_segment_keys("cold_lead", keys)
        assert result == []

    async def test_returns_empty_for_referral_funnel(self, manager):
        """referral_bonus не в KEY_SEGMENT_TO_FUNNEL → segment_keys = []."""
        assert "referral_bonus" not in KEY_SEGMENT_TO_FUNNEL.values()
        keys = [make_key()]
        result = await manager._get_segment_keys("referral_bonus", keys)
        assert result == []

    async def test_returns_empty_when_user_has_no_keys(self, manager):
        """Для ключевой воронки с пустым user_keys → []."""
        funnel_id = list(KEY_SEGMENT_TO_FUNNEL.values())[0]
        result = await manager._get_segment_keys(funnel_id, [])
        assert result == []

    async def test_calls_seg_service_for_key_based_funnel(self, manager):
        """Для key_expiry_24h вызывается KeySegmentationService.segmenter.filter_keys."""
        funnel_id = "key_expiry_24h"
        assert funnel_id in KEY_SEGMENT_TO_FUNNEL.values()

        expected_keys = [make_key()]
        manager._seg_service = MagicMock()
        manager._seg_service.segmenter = MagicMock()
        manager._seg_service.segmenter.filter_keys = AsyncMock(
            return_value=expected_keys
        )

        result = await manager._get_segment_keys(funnel_id, [make_key(), make_key()])
        assert result == expected_keys
        manager._seg_service.segmenter.filter_keys.assert_called_once()
