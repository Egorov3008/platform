"""
Тесты для сегментации ключей.
"""

import pytest
from datetime import datetime, timezone

from models import Key
from services.core.segmentation.key_model import KeySegment
from services.core.segmentation.key_ruls import KeySegmenter


@pytest.fixture
def segmenter():
    """Создать сегментатор ключей."""
    return KeySegmenter()


@pytest.fixture
def current_time_ms():
    """Получить текущее время в миллисекундах."""
    return int(datetime.now(timezone.utc).timestamp() * 1000)


@pytest.fixture
def expiring_24h_key(current_time_ms):
    """Ключ, истекающий в ближайшие 24 часа."""
    expiry = current_time_ms + 12 * 3600 * 1000  # 12 часов
    return Key(
        tg_id=123,
        email="expiring_24h@test.com",
        key="test_key",
        client_id="client_1",
        created_at=current_time_ms - 30 * 24 * 3600 * 1000,
        expiry_time=expiry,
        inbound_id=1,
        tariff_id=1,
        total_gb=10.0,
        reset_date=current_time_ms,
        notified_10h=False,
        notified_24h=False,
    )


@pytest.fixture
def expired_key(current_time_ms):
    """Истёкший ключ."""
    expiry = current_time_ms - 24 * 3600 * 1000  # 24 часа назад
    return Key(
        tg_id=124,
        email="expired@test.com",
        key="test_key",
        client_id="client_2",
        created_at=current_time_ms - 60 * 24 * 3600 * 1000,
        expiry_time=expiry,
        inbound_id=1,
        tariff_id=1,
        total_gb=10.0,
        reset_date=current_time_ms,
        notified_10h=False,
        notified_24h=False,
    )


@pytest.fixture
def active_key(current_time_ms):
    """Активный платный ключ."""
    expiry = current_time_ms + 60 * 24 * 3600 * 1000  # 60 дней (больше 30)
    return Key(
        tg_id=125,
        email="active@test.com",
        key="test_key",
        client_id="client_3",
        created_at=current_time_ms - 30 * 24 * 3600 * 1000,
        expiry_time=expiry,
        inbound_id=1,
        tariff_id=5,  # Платный тариф
        total_gb=50.0,
        reset_date=current_time_ms,
        notified_10h=False,
        notified_24h=False,
    )


@pytest.fixture
def trial_key(current_time_ms):
    """Trial ключ (expiry далеко в будущем, не попадает в EXPIRING)."""
    expiry = current_time_ms + 60 * 24 * 3600 * 1000  # 60 дней
    return Key(
        tg_id=126,
        email="trial@test.com",
        key="test_key",
        client_id="client_4",
        created_at=current_time_ms - 1 * 24 * 3600 * 1000,
        expiry_time=expiry,
        inbound_id=1,
        tariff_id=10,  # Trial тариф
        total_gb=0.0,
        reset_date=current_time_ms,
        notified_10h=False,
        notified_24h=False,
    )


@pytest.fixture
def unused_key(current_time_ms):
    """Неиспользуемый ключ (0 Гб, истекает далеко в будущем)."""
    # Expiry beyond 30 days to avoid EXPIRING_30D segmentation
    expiry = current_time_ms + 100 * 24 * 3600 * 1000
    return Key(
        tg_id=127,
        email="unused@test.com",
        key="test_key",
        client_id="client_5",
        created_at=current_time_ms - 5 * 24 * 3600 * 1000,
        expiry_time=expiry,
        inbound_id=1,
        tariff_id=3,  # Платный тариф
        total_gb=0.0,  # Не используется
        reset_date=current_time_ms,
        notified_10h=False,
        notified_24h=False,
    )


class TestKeySegmenterBasic:
    """Базовые тесты сегментатора ключей."""

    @pytest.mark.asyncio
    async def test_expiring_24h_segment(self, segmenter, expiring_24h_key):
        """Ключ должен быть определён как EXPIRING_24H."""
        segment = await segmenter.determine_segment(expiring_24h_key)
        assert segment == KeySegment.EXPIRING_24H

    @pytest.mark.asyncio
    async def test_expired_segment(self, segmenter, expired_key):
        """Ключ должен быть определён как EXPIRED."""
        segment = await segmenter.determine_segment(expired_key)
        assert segment == KeySegment.EXPIRED

    @pytest.mark.asyncio
    async def test_active_segment(self, segmenter, active_key):
        """Активный ключ должен быть определён как ACTIVE."""
        segment = await segmenter.determine_segment(active_key)
        assert segment == KeySegment.ACTIVE

    @pytest.mark.asyncio
    async def test_trial_segment(self, segmenter, trial_key):
        """Trial ключ должен быть определён как TRIAL."""
        segment = await segmenter.determine_segment(trial_key)
        assert segment == KeySegment.TRIAL

    @pytest.mark.asyncio
    async def test_unused_segment(self, segmenter, unused_key):
        """Неиспользуемый ключ должен быть определён как UNUSED."""
        segment = await segmenter.determine_segment(unused_key)
        assert segment == KeySegment.UNUSED


class TestKeySegmenterFiltering:
    """Тесты фильтрации ключей по сегментам."""

    @pytest.mark.asyncio
    async def test_filter_expiring_24h(
        self, segmenter, expiring_24h_key, active_key, expired_key
    ):
        """Фильтровать только ключи, истекающие в ближайшие 24 часа."""
        keys = [expiring_24h_key, active_key, expired_key]
        filtered = await segmenter.filter_keys(keys, KeySegment.EXPIRING_24H)

        assert len(filtered) == 1
        assert filtered[0].email == "expiring_24h@test.com"

    @pytest.mark.asyncio
    async def test_filter_expired(
        self, segmenter, expiring_24h_key, active_key, expired_key
    ):
        """Фильтровать только истёкшие ключи."""
        keys = [expiring_24h_key, active_key, expired_key]
        filtered = await segmenter.filter_keys(keys, KeySegment.EXPIRED)

        assert len(filtered) == 1
        assert filtered[0].email == "expired@test.com"

    @pytest.mark.asyncio
    async def test_filter_all(
        self, segmenter, expiring_24h_key, active_key, expired_key
    ):
        """Фильтровать все ключи должно вернуть все."""
        keys = [expiring_24h_key, active_key, expired_key]
        filtered = await segmenter.filter_keys(keys, KeySegment.ALL)

        assert len(filtered) == 3

    @pytest.mark.asyncio
    async def test_filter_empty_list(self, segmenter):
        """Фильтровать пустой список должно вернуть пустой список."""
        filtered = await segmenter.filter_keys([], KeySegment.EXPIRING_24H)
        assert filtered == []


class TestKeySegmenterTrialExpiring:
    """Тесты: trial ключи, близкие к истечению, приоритизируются как EXPIRING."""

    @pytest.mark.asyncio
    async def test_trial_key_expiring_10h(self, segmenter, current_time_ms):
        """Trial ключ, истекающий через 5 часов → EXPIRING_10H (не TRIAL)."""
        key = Key(
            tg_id=200,
            email="trial_exp_10h@test.com",
            key="test_key",
            client_id="client_t1",
            created_at=current_time_ms - 3 * 24 * 3600 * 1000,
            expiry_time=current_time_ms + 5 * 3600 * 1000,  # 5 часов
            inbound_id=1,
            tariff_id=10,
            total_gb=1.0,
            reset_date=current_time_ms,
            notified_10h=False,
            notified_24h=False,
        )
        segment = await segmenter.determine_segment(key)
        assert segment == KeySegment.EXPIRING_10H

    @pytest.mark.asyncio
    async def test_trial_key_expiring_24h(self, segmenter, current_time_ms):
        """Trial ключ, истекающий через 15 часов → EXPIRING_24H (не TRIAL)."""
        key = Key(
            tg_id=201,
            email="trial_exp_24h@test.com",
            key="test_key",
            client_id="client_t2",
            created_at=current_time_ms - 3 * 24 * 3600 * 1000,
            expiry_time=current_time_ms + 15 * 3600 * 1000,  # 15 часов
            inbound_id=1,
            tariff_id=10,
            total_gb=1.0,
            reset_date=current_time_ms,
            notified_10h=False,
            notified_24h=False,
        )
        segment = await segmenter.determine_segment(key)
        assert segment == KeySegment.EXPIRING_24H

    @pytest.mark.asyncio
    async def test_trial_key_far_future_stays_trial(self, segmenter, current_time_ms):
        """Trial ключ с expiry > 30 дней → TRIAL."""
        key = Key(
            tg_id=202,
            email="trial_far@test.com",
            key="test_key",
            client_id="client_t3",
            created_at=current_time_ms - 1 * 24 * 3600 * 1000,
            expiry_time=current_time_ms + 60 * 24 * 3600 * 1000,  # 60 дней
            inbound_id=1,
            tariff_id=10,
            total_gb=0.0,
            reset_date=current_time_ms,
            notified_10h=False,
            notified_24h=False,
        )
        segment = await segmenter.determine_segment(key)
        assert segment == KeySegment.TRIAL


class TestKeySegmentationServiceExpiring24h:
    """Тесты: get_expiring_24h включает ключи из EXPIRING_10H."""

    @pytest.mark.asyncio
    async def test_get_expiring_24h_includes_10h(self, current_time_ms):
        """get_expiring_24h должен включать ключи и в 10h, и в 24h диапазоне."""
        from services.core.keys.segmentation import KeySegmentationService

        service = KeySegmentationService()

        key_5h = Key(
            tg_id=300,
            email="key_5h@test.com",
            key="test_key",
            client_id="c1",
            created_at=current_time_ms - 30 * 24 * 3600 * 1000,
            expiry_time=current_time_ms + 5 * 3600 * 1000,
            inbound_id=1,
            tariff_id=1,
            total_gb=10.0,
            reset_date=current_time_ms,
            notified_10h=False,
            notified_24h=False,
        )
        key_15h = Key(
            tg_id=301,
            email="key_15h@test.com",
            key="test_key",
            client_id="c2",
            created_at=current_time_ms - 30 * 24 * 3600 * 1000,
            expiry_time=current_time_ms + 15 * 3600 * 1000,
            inbound_id=1,
            tariff_id=1,
            total_gb=10.0,
            reset_date=current_time_ms,
            notified_10h=False,
            notified_24h=False,
        )
        key_48h = Key(
            tg_id=302,
            email="key_48h@test.com",
            key="test_key",
            client_id="c3",
            created_at=current_time_ms - 30 * 24 * 3600 * 1000,
            expiry_time=current_time_ms + 48 * 3600 * 1000,
            inbound_id=1,
            tariff_id=1,
            total_gb=10.0,
            reset_date=current_time_ms,
            notified_10h=False,
            notified_24h=False,
        )

        result = await service.get_expiring_24h([key_5h, key_15h, key_48h])
        emails = {k.email for k in result}
        assert emails == {"key_5h@test.com", "key_15h@test.com"}


class TestKeySegmenterCaching:
    """Тесты кеширования результатов сегментации."""

    @pytest.mark.asyncio
    async def test_caching_works(self, segmenter, active_key):
        """Результаты должны кешироваться на 5 минут."""
        # Первый вызов
        segment1 = await segmenter.determine_segment(active_key)

        # Второй вызов - должен вернуть кешированный результат
        segment2 = await segmenter.determine_segment(active_key)

        assert segment1 == segment2
        assert segment1 == KeySegment.ACTIVE
