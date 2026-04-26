"""
Tests for TrialService - trial period processing with mocks.

TrialService.installation_trial() handles trial period setup for users.
Side-effectful: requires mocking ServiceDataModel and asyncpg.Pool.
"""

from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from models import User
from services.core.user.utils.trial import TrialService


@pytest.fixture
def mock_model_data():
    """Mock ServiceDataModel with users sub-service"""
    model_data = AsyncMock()
    model_data.users = AsyncMock()
    return model_data


@pytest.fixture
def mock_conn():
    """Mock asyncpg.Pool connection"""
    return AsyncMock()


@pytest.fixture
def sample_user():
    """Sample User for testing"""
    return User(
        tg_id=123456789,
        username="testuser",
        trial=0,
        created_at=datetime.now(),
        server_id=1,
    )


class TestTrialServiceInstallation:
    """Test TrialService.installation_trial() functionality"""

    @pytest.mark.asyncio
    async def test_installation_trial_success(
        self, mock_model_data, mock_conn, sample_user
    ):
        """installation_trial() should set trial flag for user"""
        mock_model_data.users.get_data.return_value = sample_user
        mock_model_data.users.update.return_value = None

        service = TrialService(mock_model_data)
        result = await service.installation_trial(123456789, mock_conn, trial=1)

        assert result is not None
        assert result.trial == 1
        assert result.tg_id == 123456789

    @pytest.mark.asyncio
    async def test_installation_trial_calls_get_data(
        self, mock_model_data, mock_conn, sample_user
    ):
        """installation_trial() should call user_data.get_data()"""
        mock_model_data.users.get_data.return_value = sample_user
        mock_model_data.users.update.return_value = None

        service = TrialService(mock_model_data)
        await service.installation_trial(123456789, mock_conn)

        mock_model_data.users.get_data.assert_called_once_with(123456789)

    @pytest.mark.asyncio
    async def test_installation_trial_calls_update(
        self, mock_model_data, mock_conn, sample_user
    ):
        """installation_trial() should call user_data.update()"""
        mock_model_data.users.get_data.return_value = sample_user
        mock_model_data.users.update.return_value = None

        service = TrialService(mock_model_data)
        await service.installation_trial(123456789, mock_conn, trial=1)

        # Should call update with user and tg_id dict
        mock_model_data.users.update.assert_called_once()
        call_args = mock_model_data.users.update.call_args
        assert call_args[0][0] == mock_conn
        assert call_args[0][1].trial == 1
        assert call_args[0][2] == {"tg_id": 123456789}

    @pytest.mark.asyncio
    async def test_installation_trial_user_not_found(self, mock_model_data, mock_conn):
        """installation_trial() should raise AttributeError if user not found"""
        mock_model_data.users.get_data.return_value = None

        service = TrialService(mock_model_data)

        with pytest.raises(AttributeError, match="Пользователь не найден"):
            await service.installation_trial(999999999, mock_conn)

    @pytest.mark.asyncio
    async def test_installation_trial_database_error(
        self, mock_model_data, mock_conn, sample_user
    ):
        """installation_trial() should propagate database errors"""
        mock_model_data.users.get_data.return_value = sample_user
        mock_model_data.users.update.side_effect = Exception("DB error")

        service = TrialService(mock_model_data)

        with pytest.raises(Exception, match="DB error"):
            await service.installation_trial(123456789, mock_conn)

    @pytest.mark.asyncio
    async def test_installation_trial_default_trial_value(
        self, mock_model_data, mock_conn, sample_user
    ):
        """installation_trial() should default trial=1"""
        mock_model_data.users.get_data.return_value = sample_user
        mock_model_data.users.update.return_value = None

        service = TrialService(mock_model_data)
        result = await service.installation_trial(
            123456789, mock_conn
        )  # No trial param

        assert result.trial == 1

    @pytest.mark.asyncio
    async def test_installation_trial_custom_trial_value(
        self, mock_model_data, mock_conn, sample_user
    ):
        """installation_trial() should accept custom trial value"""
        mock_model_data.users.get_data.return_value = sample_user
        mock_model_data.users.update.return_value = None

        service = TrialService(mock_model_data)
        result = await service.installation_trial(123456789, mock_conn, trial=7)

        assert result.trial == 7


class TestTrialServiceEdgeCases:
    """Test edge cases for TrialService"""

    @pytest.mark.asyncio
    async def test_installation_trial_zero_trial_days(
        self, mock_model_data, mock_conn, sample_user
    ):
        """installation_trial() should handle trial=0"""
        mock_model_data.users.get_data.return_value = sample_user
        mock_model_data.users.update.return_value = None

        service = TrialService(mock_model_data)
        result = await service.installation_trial(123456789, mock_conn, trial=0)

        assert result.trial == 0

    @pytest.mark.asyncio
    async def test_installation_trial_large_trial_days(
        self, mock_model_data, mock_conn, sample_user
    ):
        """installation_trial() should handle large trial values"""
        mock_model_data.users.get_data.return_value = sample_user
        mock_model_data.users.update.return_value = None

        service = TrialService(mock_model_data)
        result = await service.installation_trial(123456789, mock_conn, trial=365)

        assert result.trial == 365


class TestTrialServiceIntegration:
    """Integration tests for TrialService"""

    @pytest.mark.asyncio
    async def test_installation_trial_preserves_user_data(
        self, mock_model_data, mock_conn, sample_user
    ):
        """installation_trial() should preserve other user fields"""
        mock_model_data.users.get_data.return_value = sample_user
        mock_model_data.users.update.return_value = None

        service = TrialService(mock_model_data)
        result = await service.installation_trial(123456789, mock_conn)

        # Other fields should remain unchanged
        assert result.tg_id == sample_user.tg_id
        assert result.username == sample_user.username
        assert result.server_id == sample_user.server_id

    @pytest.mark.asyncio
    async def test_installation_trial_idempotent(
        self, mock_model_data, mock_conn, sample_user
    ):
        """Multiple calls should be idempotent"""
        mock_model_data.users.get_data.return_value = sample_user
        mock_model_data.users.update.return_value = None

        service = TrialService(mock_model_data)

        result1 = await service.installation_trial(123456789, mock_conn, trial=1)
        result2 = await service.installation_trial(123456789, mock_conn, trial=1)

        assert result1.trial == result2.trial == 1
        assert mock_model_data.users.update.call_count == 2
