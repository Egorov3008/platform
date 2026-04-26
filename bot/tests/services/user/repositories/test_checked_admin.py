from unittest.mock import patch

from services.core.user.utils.checked_admin import CheckedUser


def test_checked_user_init(checker_user):
    """Тест инициализации класса CheckedUser."""
    assert isinstance(checker_user, CheckedUser)


def test_checked_user_check_admin():
    """Тест проверки администратора."""
    with patch("services.core.user.utils.checked_admin.ADMIN_ID", [123, 456]):
        checked_user = CheckedUser()

        assert checked_user.check(123) is True
        assert checked_user.check(456) is True


def test_checked_user_check_not_admin():
    """Тест проверки не администратора."""
    with patch("services.core.user.utils.checked_admin.ADMIN_ID", [123, 456]):
        checked_user = CheckedUser()

        assert checked_user.check(789) is False
        assert checked_user.check(000) is False
