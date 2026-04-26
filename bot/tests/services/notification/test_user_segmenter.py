"""
Тесты для UserSegmenter и condition-фабрик из services/notification/core.py.

Все тесты используют фиксированное время через unittest.mock.patch,
чтобы не зависеть от реального времени выполнения.
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from models import User, Key
from services.notification.core import (
    UserSegmenter,
    UserSegment,
    new_user_condition,
    cold_lead_condition,
    inactive_trial_condition,
    expiring_keys_condition,
)

# Фиксированное «сейчас» для всех тестов
# Используем наивный datetime — так же, как datetime.now() без tzinfo в core.py.
_FIXED_NOW_NAIVE = datetime(2025, 12, 16, 12, 0, 0)
_FIXED_NOW = _FIXED_NOW_NAIVE.replace(tzinfo=timezone.utc)
# _FIXED_NOW_MS вычислен из наивного datetime — совпадает с тем, что вернёт мок
_FIXED_NOW_MS = int(_FIXED_NOW_NAIVE.timestamp() * 1000)


def make_user(
    tg_id: int = 123456,
    trial: int = 0,
    is_blocked: bool = False,
    referral_id=None,
    created_at=None,
) -> User:
    return User(
        tg_id=tg_id,
        trial=trial,
        is_blocked=is_blocked,
        referral_id=referral_id,
        created_at=created_at or _FIXED_NOW_NAIVE - timedelta(days=7),
    )


def make_key(
    email: str = "test@example.com",
    tg_id: int = 123456,
    tariff_id: int = 10,
    expiry_time: int | None = None,
    notified_24h: bool = False,
    total_gb: int = 0,
    created_at: int | None = None,
) -> Key:
    if expiry_time is None:
        expiry_time = _FIXED_NOW_MS + 12 * 3600 * 1000  # через 12 часов
    if created_at is None:
        created_at = _FIXED_NOW_MS - 3 * 24 * 3600 * 1000  # 3 дня назад
    return Key(
        tg_id=tg_id,
        email=email,
        client_id="cli_1",
        expiry_time=expiry_time,
        key="vless://...",
        inbound_id=1,
        tariff_id=tariff_id,
        notified_24h=notified_24h,
        total_gb=total_gb,
        created_at=created_at,
    )


def make_user_data(user: User, keys=None) -> dict:
    return {"user": user, "keys": keys or []}


# ---------------------------------------------------------------------------
# Тесты condition-фабрик
# ---------------------------------------------------------------------------


class TestNewUserCondition:
    """Тесты для new_user_condition(): trial=0, нет ключей, 1-15 дней."""

    async def test_returns_true_for_7_day_old_user(self):
        cond = new_user_condition()
        user = make_user(trial=0, created_at=_FIXED_NOW_NAIVE - timedelta(days=7))
        with patch("services.notification.core.datetime") as mock_dt:
            mock_dt.now.return_value = _FIXED_NOW
            result = await cond.check({"user": user, "keys": []})
        assert result is True

    async def test_returns_false_if_has_keys(self):
        cond = new_user_condition()
        user = make_user(trial=0, created_at=_FIXED_NOW_NAIVE - timedelta(days=7))
        key = make_key()
        with patch("services.notification.core.datetime") as mock_dt:
            mock_dt.now.return_value = _FIXED_NOW
            result = await cond.check({"user": user, "keys": [key]})
        assert result is False

    async def test_returns_false_if_trial_nonzero(self):
        cond = new_user_condition()
        user = make_user(trial=1, created_at=_FIXED_NOW_NAIVE - timedelta(days=7))
        with patch("services.notification.core.datetime") as mock_dt:
            mock_dt.now.return_value = _FIXED_NOW
            result = await cond.check({"user": user, "keys": []})
        assert result is False

    async def test_returns_false_if_registered_less_than_1_day(self):
        cond = new_user_condition()
        user = make_user(trial=0, created_at=_FIXED_NOW_NAIVE - timedelta(hours=12))
        with patch("services.notification.core.datetime") as mock_dt:
            mock_dt.now.return_value = _FIXED_NOW
            result = await cond.check({"user": user, "keys": []})
        assert result is False

    async def test_returns_false_if_registered_more_than_15_days(self):
        cond = new_user_condition()
        user = make_user(trial=0, created_at=_FIXED_NOW_NAIVE - timedelta(days=20))
        with patch("services.notification.core.datetime") as mock_dt:
            mock_dt.now.return_value = _FIXED_NOW
            result = await cond.check({"user": user, "keys": []})
        assert result is False

    async def test_returns_true_at_boundary_day_1(self):
        cond = new_user_condition()
        user = make_user(trial=0, created_at=_FIXED_NOW_NAIVE - timedelta(days=1))
        with patch("services.notification.core.datetime") as mock_dt:
            mock_dt.now.return_value = _FIXED_NOW
            result = await cond.check({"user": user, "keys": []})
        assert result is True

    async def test_returns_true_at_boundary_day_15(self):
        cond = new_user_condition()
        user = make_user(trial=0, created_at=_FIXED_NOW_NAIVE - timedelta(days=15))
        with patch("services.notification.core.datetime") as mock_dt:
            mock_dt.now.return_value = _FIXED_NOW
            result = await cond.check({"user": user, "keys": []})
        assert result is True


class TestColdLeadCondition:
    """Тесты для cold_lead_condition(): trial=0, нет ключей, >15 дней."""

    async def test_returns_true_for_old_user(self):
        cond = cold_lead_condition()
        user = make_user(trial=0, created_at=_FIXED_NOW_NAIVE - timedelta(days=45))
        with patch("services.notification.core.datetime") as mock_dt:
            mock_dt.now.return_value = _FIXED_NOW
            result = await cond.check({"user": user, "keys": []})
        assert result is True

    async def test_returns_false_for_user_with_trial(self):
        cond = cold_lead_condition()
        user = make_user(trial=1, created_at=_FIXED_NOW_NAIVE - timedelta(days=45))
        with patch("services.notification.core.datetime") as mock_dt:
            mock_dt.now.return_value = _FIXED_NOW
            result = await cond.check({"user": user, "keys": []})
        assert result is False

    async def test_returns_false_if_user_has_keys(self):
        cond = cold_lead_condition()
        user = make_user(trial=0, created_at=_FIXED_NOW_NAIVE - timedelta(days=45))
        key = make_key()
        with patch("services.notification.core.datetime") as mock_dt:
            mock_dt.now.return_value = _FIXED_NOW
            result = await cond.check({"user": user, "keys": [key]})
        assert result is False

    async def test_returns_false_for_16_day_old_user(self):
        """16 дней = cold lead (граница: >15)."""
        cond = cold_lead_condition()
        user = make_user(trial=0, created_at=_FIXED_NOW_NAIVE - timedelta(days=16))
        with patch("services.notification.core.datetime") as mock_dt:
            mock_dt.now.return_value = _FIXED_NOW
            result = await cond.check({"user": user, "keys": []})
        assert result is True

    async def test_returns_false_for_15_day_old_user(self):
        """15 дней — ещё не cold lead (граница строгая: >15)."""
        cond = cold_lead_condition()
        user = make_user(trial=0, created_at=_FIXED_NOW_NAIVE - timedelta(days=15))
        with patch("services.notification.core.datetime") as mock_dt:
            mock_dt.now.return_value = _FIXED_NOW
            result = await cond.check({"user": user, "keys": []})
        assert result is False


class TestInactiveTrialCondition:
    """Тесты для inactive_trial_condition(): trial=1, есть неиспользуемые trial-ключи >2 дней."""

    async def test_returns_true_for_inactive_trial(self):
        cond = inactive_trial_condition()
        user = make_user(trial=1)
        key = make_key(
            tariff_id=10,
            total_gb=0,
            created_at=_FIXED_NOW_MS - 3 * 24 * 3600 * 1000,
        )
        # inactive_trial_condition вызывает datetime.now(timezone.utc) — нужен UTC-aware ответ
        with patch("services.notification.core.datetime") as mock_dt:
            mock_dt.now.return_value = _FIXED_NOW
            mock_dt.fromtimestamp = datetime.fromtimestamp
            mock_dt.now.side_effect = lambda _=None: _FIXED_NOW
            result = await cond.check({"user": user, "keys": [key]})
        assert result is True

    async def test_returns_false_if_trial_is_zero(self):
        cond = inactive_trial_condition()
        user = make_user(trial=0)
        key = make_key(
            tariff_id=10, total_gb=0, created_at=_FIXED_NOW_MS - 3 * 24 * 3600 * 1000
        )
        # inactive_trial_condition вызывает datetime.now(timezone.utc) — нужен UTC-aware ответ
        with patch("services.notification.core.datetime") as mock_dt:
            mock_dt.now.side_effect = lambda _=None: _FIXED_NOW
            mock_dt.fromtimestamp = datetime.fromtimestamp
            result = await cond.check({"user": user, "keys": [key]})
        assert result is False

    async def test_returns_false_if_key_used(self):
        cond = inactive_trial_condition()
        user = make_user(trial=1)
        key = make_key(
            tariff_id=10,
            total_gb=5,  # использован
            created_at=_FIXED_NOW_MS - 3 * 24 * 3600 * 1000,
        )
        with patch("services.notification.core.datetime") as mock_dt:
            mock_dt.now.side_effect = lambda _=None: _FIXED_NOW
            mock_dt.fromtimestamp = datetime.fromtimestamp
            result = await cond.check({"user": user, "keys": [key]})
        assert result is False

    async def test_returns_false_if_key_too_fresh(self):
        """Ключ создан 1 день назад — условие не выполнено (нужно >2 дней)."""
        cond = inactive_trial_condition()
        user = make_user(trial=1)
        key = make_key(
            tariff_id=10,
            total_gb=0,
            created_at=_FIXED_NOW_MS - 1 * 24 * 3600 * 1000,
        )
        with patch("services.notification.core.datetime") as mock_dt:
            mock_dt.now.side_effect = lambda _=None: _FIXED_NOW
            mock_dt.fromtimestamp = datetime.fromtimestamp
            result = await cond.check({"user": user, "keys": [key]})
        assert result is False


class TestExpiringKeysCondition:
    """Тесты для expiring_keys_condition()."""

    async def test_returns_true_when_key_expires_within_24h(self):
        cond = expiring_keys_condition(24)
        key = make_key(expiry_time=_FIXED_NOW_MS + 12 * 3600 * 1000)
        with patch("services.notification.core.datetime") as mock_dt:
            mock_dt.now.return_value = _FIXED_NOW_NAIVE
            result = await cond.check({"user": make_user(), "keys": [key]})
        assert result is True

    async def test_returns_false_when_key_expires_after_24h(self):
        cond = expiring_keys_condition(24)
        key = make_key(expiry_time=_FIXED_NOW_MS + 25 * 3600 * 1000)
        with patch("services.notification.core.datetime") as mock_dt:
            mock_dt.now.return_value = _FIXED_NOW_NAIVE
            result = await cond.check({"user": make_user(), "keys": [key]})
        assert result is False

    async def test_returns_false_when_key_already_expired(self):
        cond = expiring_keys_condition(24)
        key = make_key(expiry_time=_FIXED_NOW_MS - 3600 * 1000)
        with patch("services.notification.core.datetime") as mock_dt:
            mock_dt.now.return_value = _FIXED_NOW_NAIVE
            result = await cond.check({"user": make_user(), "keys": [key]})
        assert result is False

    async def test_returns_false_when_no_keys(self):
        cond = expiring_keys_condition(24)
        with patch("services.notification.core.datetime") as mock_dt:
            mock_dt.now.return_value = _FIXED_NOW_NAIVE
            result = await cond.check({"user": make_user(), "keys": []})
        assert result is False


# ---------------------------------------------------------------------------
# Тесты UserSegmenter
# ---------------------------------------------------------------------------


class TestUserSegmenter:
    """Тесты для UserSegmenter.determine_segment()."""

    @pytest.fixture
    def segmenter(self):
        return UserSegmenter()

    async def test_returns_inactive_when_no_user(self, segmenter):
        segment = await segmenter.determine_segment({"user": None})
        assert segment == UserSegment.INACTIVE

    async def test_new_user_segment(self, segmenter):
        """trial=0, нет ключей, 7 дней → NEW_USER."""
        user = make_user(trial=0, created_at=_FIXED_NOW_NAIVE - timedelta(days=7))
        with patch("services.notification.core.datetime") as mock_dt:
            mock_dt.now.return_value = _FIXED_NOW
            segment = await segmenter.determine_segment(make_user_data(user))
        assert segment == UserSegment.NEW_USER

    async def test_too_recent_user_not_new_user(self, segmenter):
        """Зарегистрирован менее 1 дня назад — не NEW_USER."""
        user = make_user(trial=0, created_at=_FIXED_NOW_NAIVE - timedelta(hours=12))
        with patch("services.notification.core.datetime") as mock_dt:
            mock_dt.now.return_value = _FIXED_NOW
            segment = await segmenter.determine_segment(make_user_data(user))
        assert segment != UserSegment.NEW_USER
        assert segment == UserSegment.INACTIVE

    async def test_cold_lead_segment(self, segmenter):
        """trial=0, нет ключей, 45 дней → COLD_LEAD."""
        user = make_user(trial=0, created_at=_FIXED_NOW_NAIVE - timedelta(days=45))
        with patch("services.notification.core.datetime") as mock_dt:
            mock_dt.now.return_value = _FIXED_NOW
            segment = await segmenter.determine_segment(make_user_data(user))
        assert segment == UserSegment.COLD_LEAD

    async def test_new_user_too_old_becomes_cold_lead(self, segmenter):
        """trial=0, нет ключей, 20 дней → COLD_LEAD (не NEW_USER)."""
        user = make_user(trial=0, created_at=_FIXED_NOW_NAIVE - timedelta(days=20))
        with patch("services.notification.core.datetime") as mock_dt:
            mock_dt.now.return_value = _FIXED_NOW
            segment = await segmenter.determine_segment(make_user_data(user))
        assert segment == UserSegment.COLD_LEAD

    async def test_inactive_trial_segment(self, segmenter):
        """trial=1, неиспользуемый trial-ключ 3 дня → INACTIVE_TRIAL.

        Expiry_time выставляем за пределами 24ч-окна (через 7 дней),
        чтобы EXPIRING_SOON не срабатывал раньше INACTIVE_TRIAL.

        inactive_trial_condition использует datetime.now(timezone.utc) → UTC-aware.
        expiring_keys_condition использует datetime.now() без аргумента → наивный.
        Мок возвращает UTC-aware datetime для обоих вызовов — fromtimestamp тоже UTC-aware.
        """
        user = make_user(trial=1)
        key = make_key(
            tariff_id=10,
            total_gb=0,
            created_at=_FIXED_NOW_MS - 3 * 24 * 3600 * 1000,
            # expiry_time далеко в будущем — не попадает в EXPIRING_SOON
            expiry_time=_FIXED_NOW_MS + 7 * 24 * 3600 * 1000,
        )

        def _now_side_effect(_=None):
            """Возвращает UTC-aware datetime для обоих вызовов."""
            return _FIXED_NOW

        with patch("services.notification.core.datetime") as mock_dt:
            mock_dt.now.side_effect = _now_side_effect
            mock_dt.fromtimestamp = datetime.fromtimestamp
            segment = await segmenter.determine_segment(make_user_data(user, [key]))
        assert segment == UserSegment.INACTIVE_TRIAL

    async def test_inactive_trial_used_key_not_inactive_trial(self, segmenter):
        """trial=1, но ключ использовался → не INACTIVE_TRIAL."""
        user = make_user(trial=1)
        key = make_key(
            tariff_id=10,
            total_gb=5,  # использован
            created_at=_FIXED_NOW_MS - 3 * 24 * 3600 * 1000,
        )
        with patch("services.notification.core.datetime") as mock_dt:
            mock_dt.now.return_value = _FIXED_NOW
            mock_dt.fromtimestamp = datetime.fromtimestamp
            segment = await segmenter.determine_segment(make_user_data(user, [key]))
        assert segment != UserSegment.INACTIVE_TRIAL

    async def test_expiring_soon_segment(self, segmenter):
        """Ключ истекает через 22 часа → EXPIRING_SOON."""
        user = make_user()
        key = make_key(expiry_time=_FIXED_NOW_MS + 22 * 3600 * 1000)
        with patch("services.notification.core.datetime") as mock_dt:
            mock_dt.now.return_value = _FIXED_NOW_NAIVE
            segment = await segmenter.determine_segment(make_user_data(user, [key]))
        assert segment == UserSegment.EXPIRING_SOON

    async def test_inactive_when_no_matching_segment(self, segmenter):
        """Пользователь trial=2, нет ключей → INACTIVE."""
        user = make_user(trial=2, created_at=_FIXED_NOW_NAIVE - timedelta(days=5))
        with patch("services.notification.core.datetime") as mock_dt:
            mock_dt.now.return_value = _FIXED_NOW
            segment = await segmenter.determine_segment(make_user_data(user))
        assert segment == UserSegment.INACTIVE

    async def test_segment_caching(self, segmenter):
        """Одинаковый сегмент возвращается при повторном вызове (кеш)."""
        user = make_user(
            tg_id=987654, trial=0, created_at=_FIXED_NOW_NAIVE - timedelta(days=7)
        )
        with patch("services.notification.core.datetime") as mock_dt:
            mock_dt.now.return_value = _FIXED_NOW
            first = await segmenter.determine_segment(make_user_data(user))
            second = await segmenter.determine_segment(make_user_data(user))
        assert first == second
        assert len(segmenter._cache) >= 1
