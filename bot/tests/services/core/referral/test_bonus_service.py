"""
Тесты для ReferralBonusService.
"""
from unittest.mock import AsyncMock

import pytest

from models import User
from services.core.referral.bonus_service import ReferralBonusService
from services.core.data.service import ServiceDataModel


@pytest.fixture
def mock_service():
    service = AsyncMock(spec=ServiceDataModel)
    service.users = AsyncMock()
    service.data_service = AsyncMock()
    service.data_service.referral_rewards = AsyncMock()
    return service


@pytest.fixture
def bonus_service(mock_service):
    svc = ReferralBonusService(mock_service)
    svc._users = mock_service.users
    svc._data_service = mock_service.data_service
    svc._notify_referrer = AsyncMock()
    return svc


@pytest.fixture
def mock_pool():
    return AsyncMock()


@pytest.fixture
def referred_user():
    """Пользователь, пришедший по реферальной ссылке."""
    return User(tg_id=200, referral_id=100, check_referral=False)


@pytest.fixture
def non_referral_user():
    """Пользователь без реферальной ссылки."""
    return User(tg_id=300, referral_id=None, check_referral=False)


@pytest.fixture
def already_rewarded_user():
    """Пользователь, бонус уже начислен."""
    return User(tg_id=400, referral_id=100, check_referral=True)


@pytest.fixture
def referrer_user():
    """Реферер (пригласивший)."""
    return User(tg_id=100, balance=0.0)


class TestProcessReferralBonus:
    async def test_creates_reward_for_referrer(
        self, bonus_service, mock_service, mock_pool, referred_user, referrer_user
    ):
        mock_service.users.get_data = AsyncMock(
            side_effect=[referred_user, referrer_user]
        )
        mock_service.users.update = AsyncMock()

        await bonus_service.process_referral_bonus(mock_pool, 200, 500.0)

        mock_service.data_service.referral_rewards.create.assert_called_once()
        call_kwargs = mock_service.data_service.referral_rewards.create.call_args
        # Проверяем что награда для referrer_tg_id=100
        assert call_kwargs[1]["referrer_tg_id"] == 100
        assert call_kwargs[1]["reward_type"] == "discount"
        # 10% от 500 = 50.0
        assert call_kwargs[1]["reward_value"] == "50.0"

    async def test_marks_check_referral_true(
        self, bonus_service, mock_service, mock_pool, referred_user, referrer_user
    ):
        mock_service.users.get_data = AsyncMock(
            side_effect=[referred_user, referrer_user]
        )
        mock_service.users.update = AsyncMock()

        await bonus_service.process_referral_bonus(mock_pool, 200, 500.0)

        # update вызывается дважды: для referrer.balance и для referred.check_referral
        assert mock_service.users.update.call_count == 2
        # Второй вызов — пометка check_referral
        updated_user = mock_service.users.update.call_args_list[1][0][1]
        assert updated_user.check_referral is True

    async def test_skips_non_referral_user(
        self, bonus_service, mock_service, mock_pool, non_referral_user
    ):
        mock_service.users.get_data = AsyncMock(return_value=non_referral_user)

        await bonus_service.process_referral_bonus(mock_pool, 300, 500.0)

        mock_service.data_service.referral_rewards.create.assert_not_called()

    async def test_skips_already_rewarded_user(
        self, bonus_service, mock_service, mock_pool, already_rewarded_user
    ):
        mock_service.users.get_data = AsyncMock(return_value=already_rewarded_user)

        await bonus_service.process_referral_bonus(mock_pool, 400, 500.0)

        mock_service.data_service.referral_rewards.create.assert_not_called()

    async def test_skips_when_user_not_found(
        self, bonus_service, mock_service, mock_pool
    ):
        mock_service.users.get_data = AsyncMock(return_value=None)

        await bonus_service.process_referral_bonus(mock_pool, 999, 500.0)

        mock_service.data_service.referral_rewards.create.assert_not_called()

    async def test_bonus_calculation_uses_config_percentage(
        self, bonus_service, mock_service, mock_pool, referred_user, referrer_user
    ):
        mock_service.users.get_data = AsyncMock(
            side_effect=[referred_user, referrer_user]
        )
        mock_service.users.update = AsyncMock()

        await bonus_service.process_referral_bonus(mock_pool, 200, 1000.0)

        call_kwargs = mock_service.data_service.referral_rewards.create.call_args
        # 10% от 1000 = 100.0
        assert call_kwargs[1]["reward_value"] == "100.0"

    async def test_increments_referrer_balance(
        self, bonus_service, mock_service, mock_pool, referred_user, referrer_user
    ):
        """Проверяем что баланс реферера увеличивается на сумму бонуса."""
        # get_data вызывается дважды: для referred_user и для referrer
        mock_service.users.get_data = AsyncMock(
            side_effect=[referred_user, referrer_user]
        )
        mock_service.users.update = AsyncMock()

        await bonus_service.process_referral_bonus(mock_pool, 200, 500.0)

        # 10% от 500 = 50.0
        assert referrer_user.balance == 50.0
        # update вызван дважды: для referrer.balance и для referred.check_referral
        assert mock_service.users.update.call_count == 2

    async def test_increments_referrer_balance_adds_to_existing(
        self, bonus_service, mock_service, mock_pool, referred_user
    ):
        """Баланс прибавляется к существующему."""
        referrer_with_balance = User(tg_id=100, balance=100.0)
        mock_service.users.get_data = AsyncMock(
            side_effect=[referred_user, referrer_with_balance]
        )
        mock_service.users.update = AsyncMock()

        await bonus_service.process_referral_bonus(mock_pool, 200, 500.0)

        # 100.0 + 50.0 = 150.0
        assert referrer_with_balance.balance == 150.0
