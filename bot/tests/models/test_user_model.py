from models.users.user import User


class TestUser:
    def test_user_creation(self):
        user = User(tg_id=123, username="test", first_name="Test", last_name="User")
        assert user.tg_id == 123
        assert user.username == "test"
        assert user.first_name == "Test"
        assert user.last_name == "User"

    def test_user_defaults(self):
        user = User(tg_id=123)
        assert user.username is None
        assert user.first_name is None
        assert user.last_name is None
        assert user.is_blocked is False
