import pytest

from models import User, Key


@pytest.mark.asyncio
async def test_set_panel_data(cache_comparator, sample_client):  # noqa: PT019, PT006
    """Тест установки данных с панели."""
    clients = [sample_client]
    cache_comparator.set_panel_data(clients)

    assert cache_comparator.keys_panel == ["test@example.com"]
    assert cache_comparator.users_panel == [12345]


@pytest.mark.asyncio
async def test_set_cache_data(cache_comparator, mock_model_data):  # noqa: PT019, PT006
    """Тест загрузки данных из кэша."""
    # Настройка мока данных кэша
    mock_users = [User(tg_id=12345, username="test")]
    mock_keys = [
        Key(
            email="test",
            tg_id=12345,
            client_id="test",
            expiry_time=1234567890,
            key="test_key",
            inbound_id=2,
        )
    ]

    mock_model_data.users.get_all.return_value = mock_users
    mock_model_data.keys.get_all.return_value = mock_keys

    await cache_comparator.set_cache_data(
        get_all_keys_func=mock_model_data.keys.get_all,
        get_all_users_func=mock_model_data.users.get_all,
    )

    assert cache_comparator.keys_cache == [mock_keys[0].email]
    assert cache_comparator.users_cache == [12345]


@pytest.mark.asyncio
async def test_compare(cache_comparator, sample_client):  # noqa: PT019, PT006
    """Тест сравнения данных."""
    # Устанавливаем данные с панели
    cache_comparator.set_panel_data([sample_client])

    # Устанавливаем данные из кэша (отсутствует ключ)
    cache_comparator.keys_cache = []
    cache_comparator.users_cache = []

    out_keys, out_users = cache_comparator.compare()

    assert out_keys == ["test@example.com"]
    assert out_users == [12345]


@pytest.mark.asyncio
async def test_compare_no_differences(cache_comparator, sample_client):  # noqa: PT019, PT006
    """Тест сравнения без различий."""
    cache_comparator.set_panel_data([sample_client])
    cache_comparator.keys_cache = ["test@example.com"]
    cache_comparator.users_cache = [12345]

    out_keys, out_users = cache_comparator.compare()

    assert out_keys == []
    assert out_users == []
