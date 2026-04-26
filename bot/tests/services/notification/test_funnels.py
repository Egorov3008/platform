"""
Тесты для всех 4 воронок уведомлений:
- KeyExpiryFunnel24h
- TrialReminderFunnel
- ColdLeadFunnel
- ReferralBonusFunnel
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from models import User, Key
from services.notification.models import NotificationContext
from services.notification.funnels.key_expiry_24h import KeyExpiryFunnel24h
from services.notification.funnels.trial_reminder import TrialReminderFunnel
from services.notification.funnels.cold_lead_engagement import ColdLeadFunnel
from services.notification.funnels.referral_bonus import ReferralBonusFunnel
from services.notification.funnels.referral_reminder import ReferralReminderFunnel


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW_MS = int(datetime.now().timestamp() * 1000)


def make_user(
    tg_id: int = 123456,
    trial: int = 0,
    is_blocked: bool = False,
    referral_id=None,
) -> User:
    return User(
        tg_id=tg_id,
        trial=trial,
        is_blocked=is_blocked,
        referral_id=referral_id,
        created_at=datetime.now() - timedelta(days=7),
    )


def make_key(
    email: str = "test@example.com",
    tg_id: int = 123456,
    tariff_id: int = 2,
    expiry_time: int | None = None,
    notified_24h: bool = False,
    used_traffic: float = 0.0,
    total_gb: int = 0,
    created_at: int | None = None,
) -> Key:
    if expiry_time is None:
        expiry_time = _NOW_MS + 12 * 3600 * 1000
    if created_at is None:
        created_at = _NOW_MS - 3 * 24 * 3600 * 1000
    return Key(
        tg_id=tg_id,
        email=email,
        client_id="cli_1",
        expiry_time=expiry_time,
        key="vless://...",
        inbound_id=1,
        tariff_id=tariff_id,
        notified_24h=notified_24h,
        used_traffic=used_traffic,
        total_gb=total_gb,
        created_at=created_at,
    )


def make_ctx(
    user: User | None = None,
    keys: list | None = None,
    segment_keys: list | None = None,
) -> NotificationContext:
    return NotificationContext(
        user=user or make_user(),
        keys=keys if keys is not None else [],
        segment_keys=segment_keys if segment_keys is not None else [],
    )


@pytest.fixture
def mock_cache():
    cache = MagicMock()
    cache.storage = AsyncMock()
    cache.storage.get = AsyncMock(return_value=None)
    cache.storage.set = AsyncMock()
    cache.keys = AsyncMock()
    cache.keys.set = AsyncMock()
    return cache


@pytest.fixture
def mock_rate_limiter():
    rl = AsyncMock()
    rl.send_message_safe = AsyncMock(return_value="sent")
    return rl


@pytest.fixture
def mock_pool_and_conn():
    conn = AsyncMock()
    conn.execute = AsyncMock()
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=conn)
    cm.__aexit__ = AsyncMock(return_value=False)
    pool = MagicMock()
    pool.acquire = MagicMock(return_value=cm)
    return pool, conn


@pytest.fixture
def mock_bot():
    return MagicMock()


# ---------------------------------------------------------------------------
# KeyExpiryFunnel24h
# ---------------------------------------------------------------------------


class TestKeyExpiryFunnel24h:
    """Тесты для KeyExpiryFunnel24h."""

    @pytest.fixture
    def funnel(self, mock_cache, mock_pool_and_conn, mock_rate_limiter):
        pool, _ = mock_pool_and_conn
        return KeyExpiryFunnel24h(
            cache=mock_cache,
            pool=pool,
            rate_limiter=mock_rate_limiter,
        )

    async def test_should_send_false_when_no_segment_keys(self, funnel):
        ctx = make_ctx(segment_keys=[])
        assert await funnel.should_send(ctx) is False

    async def test_should_send_true_when_segment_keys_exist(self, funnel):
        ctx = make_ctx(segment_keys=[make_key()])
        assert await funnel.should_send(ctx) is True

    async def test_process_skips_already_notified_key(self, funnel):
        key = make_key(notified_24h=True)
        ctx = make_ctx(segment_keys=[key])
        result = await funnel.process(MagicMock(), ctx)
        assert result.skipped == 1
        assert result.sent == 0

    async def test_process_skips_when_deduplication_hit(self, funnel, mock_cache):
        """Ключ не уведомлён, но дедупликация уже сработала."""
        key = make_key(notified_24h=False)
        ctx = make_ctx(segment_keys=[key])
        mock_cache.storage.get.return_value = True  # дедупликация сработала
        result = await funnel.process(MagicMock(), ctx)
        assert result.skipped == 1
        assert result.sent == 0

    async def test_process_sent_updates_cache_and_db(
        self, funnel, mock_cache, mock_pool_and_conn, mock_rate_limiter
    ):
        _, conn = mock_pool_and_conn
        mock_rate_limiter.send_message_safe.return_value = "sent"
        key = make_key(notified_24h=False)
        ctx = make_ctx(segment_keys=[key])
        result = await funnel.process(MagicMock(), ctx)
        assert result.sent == 1
        assert key.notified_24h is True
        mock_cache.keys.set.assert_called_once()
        conn.execute.assert_called_once()

    async def test_process_blocked_increments_failed_blocked(
        self, funnel, mock_rate_limiter
    ):
        mock_rate_limiter.send_message_safe.return_value = "blocked"
        key = make_key(notified_24h=False)
        ctx = make_ctx(segment_keys=[key])
        result = await funnel.process(MagicMock(), ctx)
        assert result.failed_blocked == 1
        assert result.sent == 0

    async def test_process_error_increments_failed_other(
        self, funnel, mock_rate_limiter
    ):
        mock_rate_limiter.send_message_safe.return_value = "error"
        key = make_key(notified_24h=False)
        ctx = make_ctx(segment_keys=[key])
        result = await funnel.process(MagicMock(), ctx)
        assert result.failed_other == 1
        assert result.sent == 0

    async def test_process_retry_after_increments_failed_other(
        self, funnel, mock_rate_limiter
    ):
        mock_rate_limiter.send_message_safe.return_value = "retry_after"
        key = make_key(notified_24h=False)
        ctx = make_ctx(segment_keys=[key])
        result = await funnel.process(MagicMock(), ctx)
        assert result.failed_other == 1

    async def test_process_multiple_keys_mixed_results(
        self, funnel, mock_cache, mock_pool_and_conn, mock_rate_limiter
    ):
        _, _ = mock_pool_and_conn
        keys = [
            make_key(email="a@t.com", notified_24h=True),  # skipped
            make_key(email="b@t.com", notified_24h=False),  # sent
            make_key(email="c@t.com", notified_24h=False),  # sent
        ]
        mock_rate_limiter.send_message_safe.return_value = "sent"
        ctx = make_ctx(segment_keys=keys)
        result = await funnel.process(MagicMock(), ctx)
        assert result.skipped == 1
        assert result.sent == 2

    def test_funnel_id(self, funnel):
        assert funnel.funnel_id == "key_expiry_24h"


# ---------------------------------------------------------------------------
# TrialReminderFunnel
# ---------------------------------------------------------------------------


class TestTrialReminderFunnel:
    """Тесты для TrialReminderFunnel."""

    @pytest.fixture
    def funnel(self, mock_cache, mock_rate_limiter):
        return TrialReminderFunnel(cache=mock_cache, rate_limiter=mock_rate_limiter)

    async def test_should_send_false_when_no_segment_keys(self, funnel):
        ctx = make_ctx(segment_keys=[])
        assert await funnel.should_send(ctx) is False

    async def test_should_send_false_when_all_trial_keys_used(self, funnel):
        """Все trial-ключи с трафиком > 0 — пользователь уже подключался."""
        key = make_key(tariff_id=10, used_traffic=1.5, total_gb=10)
        ctx = make_ctx(segment_keys=[key])
        assert await funnel.should_send(ctx) is False

    async def test_should_send_false_when_deduplication_hit(self, funnel, mock_cache):
        key = make_key(tariff_id=10, used_traffic=0.0, total_gb=0)
        ctx = make_ctx(segment_keys=[key])
        mock_cache.storage.get.return_value = True  # дедупликация
        assert await funnel.should_send(ctx) is False

    async def test_should_send_true_for_unused_trial_key(self, funnel, mock_cache):
        key = make_key(tariff_id=10, used_traffic=0.0, total_gb=0)
        ctx = make_ctx(segment_keys=[key])
        mock_cache.storage.get.return_value = None  # нет дедупликации
        assert await funnel.should_send(ctx) is True

    async def test_process_sent_updates_dedup(
        self, funnel, mock_cache, mock_rate_limiter
    ):
        mock_rate_limiter.send_message_safe.return_value = "sent"
        ctx = make_ctx(segment_keys=[make_key(tariff_id=10)])
        result = await funnel.process(MagicMock(), ctx)
        assert result.sent == 1
        mock_cache.storage.set.assert_called_once()

    async def test_process_blocked_increments_failed_blocked(
        self, funnel, mock_rate_limiter
    ):
        mock_rate_limiter.send_message_safe.return_value = "blocked"
        ctx = make_ctx(segment_keys=[make_key(tariff_id=10)])
        result = await funnel.process(MagicMock(), ctx)
        assert result.failed_blocked == 1

    async def test_process_error_increments_failed_other(
        self, funnel, mock_rate_limiter
    ):
        mock_rate_limiter.send_message_safe.return_value = "error"
        ctx = make_ctx(segment_keys=[make_key(tariff_id=10)])
        result = await funnel.process(MagicMock(), ctx)
        assert result.failed_other == 1

    def test_funnel_id(self, funnel):
        assert funnel.funnel_id == "trial_unused"


# ---------------------------------------------------------------------------
# ColdLeadFunnel
# ---------------------------------------------------------------------------


class TestColdLeadFunnel:
    """Тесты для ColdLeadFunnel."""

    @pytest.fixture
    def funnel(self, mock_cache, mock_rate_limiter):
        return ColdLeadFunnel(cache=mock_cache, rate_limiter=mock_rate_limiter)

    async def test_should_send_false_when_trial_nonzero(self, funnel):
        ctx = make_ctx(user=make_user(trial=1))
        assert await funnel.should_send(ctx) is False

    async def test_should_send_false_when_user_has_keys(self, funnel):
        ctx = make_ctx(user=make_user(trial=0), keys=[make_key()])
        assert await funnel.should_send(ctx) is False

    async def test_should_send_false_when_deduplication_hit(self, funnel, mock_cache):
        ctx = make_ctx(user=make_user(trial=0), keys=[])
        mock_cache.storage.get.return_value = True
        assert await funnel.should_send(ctx) is False

    async def test_should_send_true_for_new_no_trial_user(self, funnel, mock_cache):
        ctx = make_ctx(user=make_user(trial=0), keys=[])
        mock_cache.storage.get.return_value = None
        assert await funnel.should_send(ctx) is True

    async def test_process_sent_updates_dedup(
        self, funnel, mock_cache, mock_rate_limiter
    ):
        mock_rate_limiter.send_message_safe.return_value = "sent"
        ctx = make_ctx(user=make_user(trial=0))
        result = await funnel.process(MagicMock(), ctx)
        assert result.sent == 1
        mock_cache.storage.set.assert_called_once()

    async def test_process_blocked_increments_failed_blocked(
        self, funnel, mock_rate_limiter
    ):
        mock_rate_limiter.send_message_safe.return_value = "blocked"
        ctx = make_ctx(user=make_user(trial=0))
        result = await funnel.process(MagicMock(), ctx)
        assert result.failed_blocked == 1

    async def test_process_error_increments_failed_other(
        self, funnel, mock_rate_limiter
    ):
        mock_rate_limiter.send_message_safe.return_value = "error"
        ctx = make_ctx(user=make_user(trial=0))
        result = await funnel.process(MagicMock(), ctx)
        assert result.failed_other == 1

    def test_funnel_id(self, funnel):
        assert funnel.funnel_id == "cold_lead"


# ---------------------------------------------------------------------------
# ReferralBonusFunnel
# ---------------------------------------------------------------------------


class TestReferralBonusFunnel:
    """Тесты для ReferralBonusFunnel."""

    @pytest.fixture
    def funnel(self, mock_cache, mock_rate_limiter):
        return ReferralBonusFunnel(cache=mock_cache, rate_limiter=mock_rate_limiter)

    async def test_should_send_false_when_referral_id_is_none(self, funnel):
        ctx = make_ctx(user=make_user(trial=0, referral_id=None))
        assert await funnel.should_send(ctx) is False

    async def test_should_send_false_when_trial_nonzero(self, funnel):
        ctx = make_ctx(user=make_user(trial=1, referral_id=999))
        assert await funnel.should_send(ctx) is False

    async def test_should_send_false_when_deduplication_hit(self, funnel, mock_cache):
        ctx = make_ctx(user=make_user(trial=0, referral_id=999))
        mock_cache.storage.get.return_value = True
        assert await funnel.should_send(ctx) is False

    async def test_should_send_true_for_new_referral_user(self, funnel, mock_cache):
        ctx = make_ctx(user=make_user(trial=0, referral_id=999))
        mock_cache.storage.get.return_value = None
        assert await funnel.should_send(ctx) is True

    async def test_process_sent_updates_dedup(
        self, funnel, mock_cache, mock_rate_limiter
    ):
        mock_rate_limiter.send_message_safe.return_value = "sent"
        ctx = make_ctx(user=make_user(trial=0, referral_id=42))
        result = await funnel.process(MagicMock(), ctx)
        assert result.sent == 1
        mock_cache.storage.set.assert_called_once()

    async def test_process_blocked_increments_failed_blocked(
        self, funnel, mock_rate_limiter
    ):
        mock_rate_limiter.send_message_safe.return_value = "blocked"
        ctx = make_ctx(user=make_user(trial=0, referral_id=42))
        result = await funnel.process(MagicMock(), ctx)
        assert result.failed_blocked == 1

    async def test_process_error_increments_failed_other(
        self, funnel, mock_rate_limiter
    ):
        mock_rate_limiter.send_message_safe.return_value = "error"
        ctx = make_ctx(user=make_user(trial=0, referral_id=42))
        result = await funnel.process(MagicMock(), ctx)
        assert result.failed_other == 1

    def test_funnel_id(self, funnel):
        assert funnel.funnel_id == "referral_bonus"


# ---------------------------------------------------------------------------
# ReferralReminderFunnel
# ---------------------------------------------------------------------------


class TestReferralReminderFunnel:
    """Тесты для ReferralReminderFunnel."""

    @pytest.fixture
    def funnel(self, mock_cache, mock_pool_and_conn, mock_rate_limiter):
        pool, _ = mock_pool_and_conn
        return ReferralReminderFunnel(
            cache=mock_cache,
            pool=pool,
            rate_limiter=mock_rate_limiter,
        )

    @pytest.fixture
    def funnel_no_link(self, mock_cache, mock_pool_and_conn, mock_rate_limiter):
        """Воронка, где у пользователя нет реф. ссылки в БД."""
        pool, conn = mock_pool_and_conn
        conn.fetchval = AsyncMock(return_value=False)  # has_link = False
        return ReferralReminderFunnel(
            cache=mock_cache,
            pool=pool,
            rate_limiter=mock_rate_limiter,
        )

    @pytest.fixture
    def funnel_has_link(self, mock_cache, mock_pool_and_conn, mock_rate_limiter):
        """Воронка, где у пользователя уже есть реф. ссылка в БД."""
        pool, conn = mock_pool_and_conn
        conn.fetchval = AsyncMock(return_value=True)  # has_link = True
        return ReferralReminderFunnel(
            cache=mock_cache,
            pool=pool,
            rate_limiter=mock_rate_limiter,
        )

    async def test_should_send_false_when_deduplication_hit(
        self, funnel_no_link, mock_cache
    ):
        ctx = make_ctx(user=make_user())
        mock_cache.storage.get.return_value = True  # уже отправляли
        assert await funnel_no_link.should_send(ctx) is False

    async def test_should_send_false_when_user_has_referral_link(
        self, funnel_has_link, mock_cache
    ):
        ctx = make_ctx(user=make_user())
        mock_cache.storage.get.return_value = None  # нет дедупликации
        assert await funnel_has_link.should_send(ctx) is False

    async def test_should_send_true_when_no_link_and_no_dedup(
        self, funnel_no_link, mock_cache
    ):
        ctx = make_ctx(user=make_user())
        mock_cache.storage.get.return_value = None
        assert await funnel_no_link.should_send(ctx) is True

    async def test_process_sent_updates_dedup(
        self, funnel_no_link, mock_cache, mock_rate_limiter
    ):
        mock_rate_limiter.send_message_safe.return_value = "sent"
        ctx = make_ctx(user=make_user())
        result = await funnel_no_link.process(MagicMock(), ctx)
        assert result.sent == 1
        mock_cache.storage.set.assert_called_once()

    async def test_process_blocked_increments_failed_blocked(
        self, funnel_no_link, mock_rate_limiter
    ):
        mock_rate_limiter.send_message_safe.return_value = "blocked"
        ctx = make_ctx(user=make_user())
        result = await funnel_no_link.process(MagicMock(), ctx)
        assert result.failed_blocked == 1
        assert result.sent == 0

    async def test_process_error_increments_failed_other(
        self, funnel_no_link, mock_rate_limiter
    ):
        mock_rate_limiter.send_message_safe.return_value = "error"
        ctx = make_ctx(user=make_user())
        result = await funnel_no_link.process(MagicMock(), ctx)
        assert result.failed_other == 1
        assert result.sent == 0

    async def test_process_retry_after_increments_failed_other(
        self, funnel_no_link, mock_rate_limiter
    ):
        mock_rate_limiter.send_message_safe.return_value = "retry_after"
        ctx = make_ctx(user=make_user())
        result = await funnel_no_link.process(MagicMock(), ctx)
        assert result.failed_other == 1

    async def test_process_not_sent_when_has_link(
        self, funnel_has_link, mock_cache, mock_rate_limiter
    ):
        """should_send вернёт False — process не должен отправить ничего."""
        mock_cache.storage.get.return_value = None
        ctx = make_ctx(user=make_user())
        assert await funnel_has_link.should_send(ctx) is False
        mock_rate_limiter.send_message_safe.assert_not_called()

    def test_funnel_id(self, funnel):
        assert funnel.funnel_id == "referral_reminder"
