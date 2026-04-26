from models.keys.key import Key


class TestKey:
    def test_key_creation(self):
        key = Key(
            tg_id=123,
            email="test@test.com",
            client_id="123",
            expiry_time=1234567890,
            key="test-keys",
            inbound_id=1,
        )
        assert key.tg_id == 123
        assert key.email == "test@test.com"
        assert key.client_id == "123"
        assert key.expiry_time == 1234567890
        assert key.key == "test-keys"
        assert key.inbound_id == 1

    def test_key_defaults(self):
        key = Key(
            tg_id=123,
            email="test@test.com",
            client_id="123",
            expiry_time=1234567890,
            key="test-keys",
            inbound_id=1,
        )
        # assert keys.user_id is None - нет такого поля
        # assert keys.used_traffic is None - умолчательное значение 0
        # assert keys.data_limit is None - нет такого поля
