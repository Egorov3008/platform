from unittest.mock import AsyncMock, Mock

import pytest

from services.core.user.utils.trial import TrialService


def make_trial_service(user_data):
    """Создаёт TrialService с мок-моделью данных."""
    model_data = Mock()
    model_data.users = user_data
    return TrialService(model_data=model_data)


def test_trial_service_init(user_data):
    """Тест инициализации класса TrialService."""
    trial_service = make_trial_service(user_data)
    assert trial_service.user_data == user_data


@pytest.mark.asyncio
async def test_installation_trial_success(user_data, mock_conn, user):
    """Тест успешной установки пробного периода."""
    trial_service = make_trial_service(user_data)
    user_data.get_data = AsyncMock(return_value=user)
    user_data.update = AsyncMock(return_value=True)

    result = await trial_service.installation_trial(user.tg_id, mock_conn, trial=1)

    user_data.get_data.assert_called_once_with(user.tg_id)
    user_data.update.assert_called_once_with(mock_conn, user, {"tg_id": user.tg_id})
    assert result is not None


@pytest.mark.asyncio
async def test_installation_trial_user_not_found(user_data, mock_conn):
    """Тест установки пробного периода при отсутствии пользователя."""
    user_id = 123
    user_data.get_data = AsyncMock(return_value=None)
    user_data.save_data = AsyncMock()

    trial_service = make_trial_service(user_data)

    with pytest.raises(AttributeError, match="Пользователь не найден"):
        await trial_service.installation_trial(user_id, mock_conn, 1)

    user_data.get_data.assert_called_once_with(user_id)
    user_data.save_data.assert_not_called()
