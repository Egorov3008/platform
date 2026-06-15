from datetime import datetime

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


class TestUserFromBackend:
    """User.from_backend() must accept the exact dict shape that
    BackendAPIClient.get_user() returns (== UserResponse from the backend).
    """

    def test_accepts_dict_from_user_response(self):
        # Verbatim copy of UserResponse fields as returned by /api/v1/users/{tg_id}
        data = {
            "tg_id": 123456789,
            "username": "alice",
            "first_name": "Alice",
            "balance": 0.0,
            "trial": 0,
            "server_id": 1,
            "is_admin": False,
            "is_blocked": False,
            "created_at": "2026-01-15T10:30:00+00:00",
        }
        user = User.from_backend(data)

        assert user.tg_id == 123456789
        assert user.username == "alice"
        assert user.first_name == "Alice"
        assert user.trial == 0
        assert user.is_admin is False
        assert user.is_blocked is False
        # Fields not in backend response keep their defaults
        assert user.last_name is None
        assert user.language_code is None

    def test_trial_used_state(self):
        """trial=1 means trial already consumed (mirrors backend)."""
        user = User.from_backend({"tg_id": 5, "trial": 1})
        assert user.trial == 1
        assert user.tg_id == 5

