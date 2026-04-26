import pytest
from datetime import datetime, timezone, timedelta

from models import User, Key
from services.core.segmentation.ruls import (
    new_user_condition,
    inactive_trial_condition,
    cold_lead_condition,
    blocked_condition,
    expiring_keys_condition,
)


class TestRuleConditions:
    @pytest.fixture
    def user_data_factory(self):
        def create(tg_id=123, trial=0, days_ago=0, keys=None):
            created_at = datetime.now(timezone.utc) - timedelta(days=days_ago)
            user = User(
                tg_id=tg_id,
                username="test_user",
                trial=trial,
                created_at=created_at,
                server_id=1,
            )
            return {"user": user, "keys": keys or []}

        return create

    @pytest.fixture
    def paid_key(self):
        return Key(
            email="paid@test.com",
            inbound_id=1,
            client_id="123",
            tg_id=123,
            key="paid_key",
            expiry_time=int(
                (datetime.now(timezone.utc) + timedelta(days=30)).timestamp() * 1000
            ),
            tariff_id=2,
            total_gb=1,
        )

    @pytest.fixture
    def trial_key(self):
        now = datetime.now(timezone.utc)
        return Key(
            email="trial@test.com",
            inbound_id=2,
            client_id="456",
            tg_id=123,
            key="trial_key",
            expiry_time=int((now + timedelta(days=30)).timestamp() * 1000),
            tariff_id=10,
            total_gb=0,
            created_at=int((now - timedelta(days=3)).timestamp() * 1000),
        )

    @pytest.mark.asyncio
    async def test_new_user_condition_valid(self, user_data_factory, paid_key):
        user_data = user_data_factory(
            trial=0, days_ago=5
        )  # новый пользователь без ключей
        condition = new_user_condition()
        assert await condition.check(user_data) is True

    @pytest.mark.asyncio
    async def test_new_user_condition_with_keys(self, user_data_factory, paid_key):
        user_data = user_data_factory(trial=0, days_ago=5, keys=[paid_key])
        condition = new_user_condition()
        assert await condition.check(user_data) is False

    @pytest.mark.asyncio
    async def test_new_user_condition_old_user(self, user_data_factory):
        user_data = user_data_factory(trial=0, days_ago=20)  # старый пользователь
        condition = new_user_condition()
        assert await condition.check(user_data) is False

    @pytest.mark.asyncio
    async def test_inactive_trial_condition_valid(self, user_data_factory, trial_key):
        user_data = user_data_factory(trial=1, keys=[trial_key])
        condition = inactive_trial_condition()
        assert await condition.check(user_data) is True

    @pytest.mark.asyncio
    async def test_inactive_trial_condition_active_trial(
        self, user_data_factory, trial_key
    ):
        # Обновляем created_at, чтобы ключ был создан менее 2 дней назад
        two_hours_ago = datetime.now(timezone.utc) - timedelta(hours=2)
        trial_key.created_at = int(two_hours_ago.timestamp() * 1000)

        user_data = user_data_factory(trial=1, keys=[trial_key])
        condition = inactive_trial_condition()
        assert await condition.check(user_data) is False

    @pytest.mark.asyncio
    async def test_inactive_trial_condition_used_trial(
        self, user_data_factory, trial_key
    ):
        trial_key.total_gb = 1  # Пользователь использовал трафик
        user_data = user_data_factory(trial=1, keys=[trial_key])
        condition = inactive_trial_condition()
        assert await condition.check(user_data) is False

    @pytest.mark.asyncio
    async def test_cold_lead_condition_valid(self, user_data_factory):
        user_data = user_data_factory(
            trial=0, days_ago=45
        )  # давно зарегистрированный, нет ключей
        condition = cold_lead_condition()
        assert await condition.check(user_data) is True

    @pytest.mark.asyncio
    async def test_cold_lead_condition_new_user(self, user_data_factory):
        user_data = user_data_factory(trial=0, days_ago=10)  # новый пользователь
        condition = cold_lead_condition()
        assert await condition.check(user_data) is False

    @pytest.mark.asyncio
    async def test_blocked_condition_valid(self, user_data_factory):
        user_data = user_data_factory()
        user_data["user"].is_blocked = True
        condition = blocked_condition()
        assert await condition.check(user_data) is True

    @pytest.mark.asyncio
    async def test_blocked_condition_not_blocked(self, user_data_factory):
        user_data = user_data_factory()
        user_data["user"].is_blocked = False
        condition = blocked_condition()
        assert await condition.check(user_data) is False

    @pytest.mark.asyncio
    async def test_expiring_keys_condition_within_24h(self, user_data_factory):
        # Ключ, который истекает через 12 часов
        expiry_time = datetime.now(timezone.utc) + timedelta(hours=12)
        key = Key(
            email="expiring@test.com",
            inbound_id=1,
            client_id="123",
            tg_id=123,
            key="expiring_key",
            expiry_time=int(expiry_time.timestamp() * 1000),
            tariff_id=2,
        )
        user_data = user_data_factory(keys=[key])
        condition = expiring_keys_condition(24)
        assert await condition.check(user_data) is True

    @pytest.mark.asyncio
    async def test_expiring_keys_condition_outside_24h(self, user_data_factory):
        # Ключ, который истекает через 48 часов
        expiry_time = datetime.now(timezone.utc) + timedelta(hours=48)
        key = Key(
            email="not_expiring@test.com",
            inbound_id=1,
            client_id="123",
            tg_id=123,
            key="not_expiring_key",
            expiry_time=int(expiry_time.timestamp() * 1000),
            tariff_id=2,
        )
        user_data = user_data_factory(keys=[key])
        condition = expiring_keys_condition(24)
        assert await condition.check(user_data) is False
