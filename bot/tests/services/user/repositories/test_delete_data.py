import pytest
from unittest.mock import AsyncMock, Mock

from services.core.user.utils.delete_data import DeleteUser


def make_delete_user(user_data, key_data, xui_session, pool):
    """Создаёт DeleteUser с мок-моделью данных."""
    model_data = Mock()
    model_data.users = user_data
    model_data.keys = key_data
    return DeleteUser(model_data=model_data, xui_session=xui_session, pool=pool)


def test_delete_user_init(user_data, key_data, mock_xui_session, mock_conn):
    """Тест инициализации класса DeleteUser."""
    delete_user = make_delete_user(user_data, key_data, mock_xui_session, mock_conn)

    assert delete_user.user_data == user_data
    assert delete_user.key_data == key_data
    assert delete_user.xui_session == mock_xui_session
    assert delete_user.pool == mock_conn


@pytest.mark.asyncio
async def test_delete_user_with_keys(user_data, key_data, mock_xui_session, mock_conn):
    """Тест удаления пользователя с ключами."""
    user_id = 123
    mock_key = AsyncMock()
    mock_key.email = "test@example.com"
    mock_key.inbound_id = 1
    mock_key.client_id = "client-uuid"
    mock_user = AsyncMock()

    key_data.get_by = AsyncMock(return_value=[mock_key])
    user_data.get_data = AsyncMock(return_value=mock_user)
    user_data.delete_data = AsyncMock()
    key_data.delete_data = AsyncMock()
    mock_xui_session.delete_client = AsyncMock(return_value=True)

    delete_user = make_delete_user(user_data, key_data, mock_xui_session, mock_conn)
    await delete_user.delete(user_id)

    key_data.get_by.assert_called_once_with(tg_id=user_id)
    user_data.get_data.assert_called_once_with(user_id)
    mock_xui_session.delete_client.assert_called_once_with(
        email=mock_key.email,
        inbound_id=mock_key.inbound_id,
        client_id=mock_key.client_id,
    )
    key_data.delete_data.assert_called_once_with(mock_conn, mock_key)
    user_data.delete_data.assert_called_once_with(mock_conn, mock_user)


@pytest.mark.asyncio
async def test_delete_user_without_keys(
    user_data, key_data, mock_xui_session, mock_conn
):
    """Тест удаления пользователя без ключей."""
    user_id = 123
    mock_user = AsyncMock()

    key_data.get_by = AsyncMock(return_value=[])
    user_data.get_data = AsyncMock(return_value=mock_user)
    user_data.delete_data = AsyncMock()

    delete_user = make_delete_user(user_data, key_data, mock_xui_session, mock_conn)
    await delete_user.delete(user_id)

    key_data.get_by.assert_called_once_with(tg_id=user_id)
    key_data.delete_data.assert_not_called()
    user_data.delete_data.assert_called_once_with(mock_conn, mock_user)
