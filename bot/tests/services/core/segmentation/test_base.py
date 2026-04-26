from typing import Dict, Any

import pytest
from datetime import datetime, timezone, timedelta

from models import User, Key
from services.core.segmentation.base import BaseCondition


class TestBaseCondition:
    @pytest.fixture
    def base_condition(self):
        # Создаём минимальный рабочий подкласс, реализующий абстрактный метод
        class ConcreteCondition(BaseCondition):
            async def check(self, user_data: Dict[str, Any]) -> bool:
                return True  # Заглушка

        return ConcreteCondition()

    @pytest.fixture
    def user_data(self):
        user = User(
            tg_id=123,
            username="test_user",
            trial=1,
            created_at=datetime.now(timezone.utc),
            server_id=1,
        )
        keys = [
            Key(
                email="test1@test.com",
                inbound_id=1,
                client_id="123",
                tg_id=123,
                key="key1",
                expiry_time=int(
                    (datetime.now(timezone.utc) + timedelta(days=30)).timestamp() * 1000
                ),
                tariff_id=2,
                total_gb=1,
            ),
            Key(
                email="test2@test.com",
                inbound_id=2,
                client_id="456",
                tg_id=123,
                key="key2",
                expiry_time=int(
                    (datetime.now(timezone.utc) - timedelta(days=5)).timestamp() * 1000
                ),
                tariff_id=10,
                total_gb=0,
            ),
        ]
        return {"user": user, "keys": keys}

    def test_get_user_and_keys_valid(self, base_condition, user_data):
        user, keys = base_condition._get_user_and_keys(user_data)
        assert user == user_data["user"]
        assert keys == user_data["keys"]

    def test_get_user_and_keys_no_user(self, base_condition):
        with pytest.raises(ValueError, match="user_data должен содержать 'user'"):
            base_condition._get_user_and_keys({"keys": []})

    def test_is_paid_tariff(self, base_condition):
        assert base_condition._is_paid_tariff(2) is True
        assert base_condition._is_paid_tariff(3) is True
        assert base_condition._is_paid_tariff(1) is True   # tariff_id=1 — платный тариф
        assert base_condition._is_paid_tariff(10) is False  # только trial исключается

    def test_filter_keys_no_filters(self, base_condition, user_data):
        keys = base_condition._filter_keys(user_data["keys"])
        assert len(keys) == 2

    def test_filter_keys_tariff_filter(self, base_condition, user_data):
        keys = base_condition._filter_keys(
            user_data["keys"], tariff_filter=lambda tid: tid == 2
        )
        assert len(keys) == 1
        assert keys[0].tariff_id == 2

    def test_filter_keys_expiry_filter_future(self, base_condition, user_data):
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        keys = base_condition._filter_keys(
            user_data["keys"], expiry_filter=lambda exp: exp >= now_ms
        )
        assert len(keys) == 1  # только активный ключ
        assert keys[0].tariff_id == 2

    def test_filter_keys_expiry_filter_past(self, base_condition, user_data):
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        keys = base_condition._filter_keys(
            user_data["keys"], expiry_filter=lambda exp: exp < now_ms
        )
        assert len(keys) == 1  # только истекший ключ
        assert keys[0].tariff_id == 10

    def test_filter_keys_usage_filter(self, base_condition, user_data):
        keys = base_condition._filter_keys(
            user_data["keys"], usage_filter=lambda usage: usage == 0.0
        )
        assert len(keys) == 1
        assert keys[0].tariff_id == 10

    def test_get_active_paid_keys(self, base_condition, user_data):
        keys = base_condition.get_active_paid_keys(user_data["keys"])
        assert len(keys) == 1
        assert keys[0].tariff_id == 2
        assert keys[0].expiry_time > base_condition.time.now_ms

    def test_get_expired_paid_keys(self, base_condition, user_data):
        keys = base_condition.get_expired_paid_keys(user_data["keys"])
        assert len(keys) == 0  # trial ключ не считается платным

    def test_get_keys_expiring_in(self, base_condition, user_data):
        # Создаем ключ, который истекает через 5 часов
        future_time = datetime.now(timezone.utc) + timedelta(hours=5)
        expiring_key = Key(
            email="expiring@test.com",
            inbound_id=3,
            client_id="789",
            tg_id=123,
            key="key3",
            expiry_time=int(future_time.timestamp() * 1000),
            tariff_id=2,
            total_gb=2,
        )
        keys_with_expiring = user_data["keys"] + [expiring_key]

        keys = base_condition.get_keys_expiring_in(keys_with_expiring, hours=10)
        assert len(keys) == 1
        assert keys[0].key == "key3"
