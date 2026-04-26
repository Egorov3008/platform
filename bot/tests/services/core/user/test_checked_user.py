"""
Tests for CheckedUser service - pure admin check logic.

CheckedUser.check() verifies if a user is in the admin list.
Pure logic: no I/O, no async, only config lookup.
"""

from unittest.mock import patch

from services.core.user.utils.checked_admin import CheckedUser


class TestCheckedUserBasic:
    """Test CheckedUser.check() with various user IDs"""

    @patch("services.core.user.utils.checked_admin.ADMIN_ID", [123, 456, 789])
    def test_check_admin_user_true(self):
        """check() should return True for admin user in list"""
        service = CheckedUser()
        assert service.check(123) is True
        assert service.check(456) is True
        assert service.check(789) is True

    @patch("services.core.user.utils.checked_admin.ADMIN_ID", [123, 456, 789])
    def test_check_regular_user_false(self):
        """check() should return False for regular user not in list"""
        service = CheckedUser()
        assert service.check(999) is False
        assert service.check(0) is False
        assert service.check(1) is False

    @patch("services.core.user.utils.checked_admin.ADMIN_ID", [123])
    def test_check_single_admin(self):
        """check() should work with single admin"""
        service = CheckedUser()
        assert service.check(123) is True
        assert service.check(999) is False

    @patch("services.core.user.utils.checked_admin.ADMIN_ID", [])
    def test_check_empty_admin_list(self):
        """check() should return False when admin list is empty"""
        service = CheckedUser()
        assert service.check(123) is False
        assert service.check(999) is False


class TestCheckedUserEdgeCases:
    """Test edge cases for CheckedUser"""

    @patch("services.core.user.utils.checked_admin.ADMIN_ID", [0, -1, 999999999])
    def test_check_zero_id(self):
        """check() should handle user_id=0"""
        service = CheckedUser()
        assert service.check(0) is True

    @patch("services.core.user.utils.checked_admin.ADMIN_ID", [0, -1, 999999999])
    def test_check_negative_id(self):
        """check() should handle negative IDs"""
        service = CheckedUser()
        assert service.check(-1) is True

    @patch("services.core.user.utils.checked_admin.ADMIN_ID", [0, -1, 999999999])
    def test_check_very_large_id(self):
        """check() should handle very large Telegram IDs"""
        service = CheckedUser()
        assert service.check(999999999) is True
        assert service.check(9999999999999) is False


class TestCheckedUserDeterminism:
    """Test that CheckedUser behaves deterministically"""

    @patch("services.core.user.utils.checked_admin.ADMIN_ID", [123, 456, 789])
    def test_check_same_user_same_result(self):
        """check() should return same result for same user_id"""
        service = CheckedUser()
        result1 = service.check(123)
        result2 = service.check(123)
        assert result1 == result2 == True

    @patch("services.core.user.utils.checked_admin.ADMIN_ID", [123, 456, 789])
    def test_check_multiple_calls_consistent(self):
        """check() should return consistent results across multiple calls"""
        service = CheckedUser()
        # Check same user multiple times
        assert service.check(999) is False
        assert service.check(456) is True
        assert service.check(999) is False
        assert service.check(123) is True
        assert service.check(999) is False

    def test_check_immutable(self):
        """CheckedUser instance should not change state"""
        service = CheckedUser()
        # Create two instances
        service1 = CheckedUser()
        service2 = CheckedUser()

        with patch("services.core.user.utils.checked_admin.ADMIN_ID", [123]):
            assert service1.check(123) is True
            assert service2.check(123) is True

        with patch("services.core.user.utils.checked_admin.ADMIN_ID", [456]):
            assert service1.check(456) is True
            assert service1.check(123) is False


class TestCheckedUserIntegration:
    """Integration tests with actual ADMIN_ID config"""

    def test_check_with_actual_config(self):
        """check() should work with actual ADMIN_ID from config"""
        service = CheckedUser()
        # Just verify the method works without error
        # Actual IDs depend on project config
        result = service.check(123)
        assert isinstance(result, bool)

    def test_check_multiple_admins(self):
        """check() should handle multiple admins in list"""
        with patch(
            "services.core.user.utils.checked_admin.ADMIN_ID",
            [111111111, 222222222, 333333333],
        ):
            service = CheckedUser()
            assert service.check(111111111) is True
            assert service.check(222222222) is True
            assert service.check(333333333) is True
            assert service.check(444444444) is False
