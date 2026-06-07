from punq import Container
import asyncpg
from database import DataService
from services.cache.service import CacheService
from services.cache.storage import CacheStorage
from services.container import create_container
from services.container.registrate.core import (
    CacheRegistrar,
    CoreServiceRegistrar,
    KeyServiceRegistrar,
    UserServiceRegistrar,
    GiftServiceRegistrar,
)

# Импорты сервисов для проверки типов
from middlewares.cache_middleware import CacheMiddleware
from client import XUISession
from services.core.keys.utils.create_key import CreateKey
from services.core.keys.utils.renewal import KeyRenewal
from services.core.user.utils.saturation import SaturationUser
from services.core.connect_module.repositories.form_data import FormConnectionData
from services.core.keys.utils.formtion import FormationKey

# Импорты сервисов ключей
from services.core.keys.utils.calculator import ExpiryCalculator

# Импорты сервисов пользователей
from services.core.user.utils.delete_data import DeleteUser
from services.core.user.utils.trial import TrialService

# Импорты сервисов подарков
from services.core.gift import TokenGen, GiftLinkProvider
from services.core.gift.repositories.checker import CheckerGiftLink


from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
async def mock_db_pool():
    """Создает мок пула базы данных."""
    pool = AsyncMock()
    pool.acquire = AsyncMock(return_value=AsyncMock())
    return pool


@pytest.fixture
async def container_with_mocks(mock_db_pool):
    container = Container()
    # Регистрируем моки зависимостей
    container.register(asyncpg.Pool, instance=mock_db_pool, scope="singleton")
    container.register(DataService, scope="singleton")
    container.register(CacheStorage, scope="singleton")

    # Создаем мок cache_service с необходимыми атрибутами
    cache_service = MagicMock()
    cache_service.users = MagicMock()
    cache_service.keys = MagicMock()
    cache_service.servers = MagicMock()
    cache_service.tariffs = MagicMock()
    cache_service.gifts = MagicMock()
    cache_service.inbounds = MagicMock()

    container.register(CacheService, instance=cache_service, scope="singleton")
    container.register(CacheMiddleware, instance=MagicMock(), scope="singleton")
    container.register(
        XUISession, instance=AsyncMock(spec=XUISession), scope="singleton"
    )
    container.register(ExpiryCalculator, instance=MagicMock(), scope="singleton")
    container.register(FormConnectionData, instance=MagicMock(), scope="singleton")
    container.register(FormationKey, instance=MagicMock(), scope="singleton")
    container.register(CreateKey, instance=MagicMock(), scope="singleton")
    container.register(KeyRenewal, instance=MagicMock(), scope="singleton")
    # container.register(UserData, instance=MagicMock(), scope="singleton")  # Удален, так как модуль не существует
    container.register(SaturationUser, instance=MagicMock(), scope="singleton")
    container.register(TrialService, instance=MagicMock(), scope="singleton")
    container.register(DeleteUser, instance=MagicMock(), scope="singleton")
    # container.register(GiftLinkData, instance=MagicMock(), scope="singleton")  # Удален, так как не существует
    container.register(CheckerGiftLink, instance=MagicMock(), scope="singleton")
    container.register(TokenGen, instance=MagicMock(), scope="singleton")
    container.register(GiftLinkProvider, instance=MagicMock(), scope="singleton")

    return container


@pytest.mark.asyncio
async def test_container_creation(mock_db_pool):
    """
    Тестирует создание контейнера зависимостей.
    Проверяет, что функция create_container корректно создает контейнер.
    """
    with patch("services.container.create_db_pool", return_value=mock_db_pool):
        container = await create_container()

    assert isinstance(container, Container)
    assert container.resolve(DataService) is not None
    assert container.resolve(asyncpg.Pool) is not None


@pytest.mark.asyncio
async def test_container_registration(container_with_mocks):
    """
    Тестирует инициализацию контейнера зависимостей.
    Проверяет, что все необходимые сервисы зарегистрированы и могут быть разрешены.
    """
    # Используем контейнер с моками
    container = container_with_mocks

    # Регистрируем регистраторы
    CacheRegistrar().register_dependencies(container)
    CoreServiceRegistrar().register_dependencies(container)
    KeyServiceRegistrar().register_dependencies(container)
    UserServiceRegistrar().register_dependencies(container)
    GiftServiceRegistrar().register_dependencies(container)

    # Проверяем регистрацию CacheRegistrar
    resolved_cache_storage = container.resolve(CacheStorage)
    assert resolved_cache_storage is not None
    assert isinstance(resolved_cache_storage, CacheStorage)

    resolved_cache_service = container.resolve(CacheService)
    assert resolved_cache_service is not None
    assert isinstance(resolved_cache_service, CacheService)

    resolved_cache_middleware = container.resolve(CacheMiddleware)
    assert resolved_cache_middleware is not None
    assert isinstance(resolved_cache_middleware, CacheMiddleware)

    # Проверяем регистрацию CoreServiceRegistrar
    resolved_xui_session = container.resolve(XUISession)
    assert resolved_xui_session is not None
    assert isinstance(resolved_xui_session, XUISession)

    # Проверяем регистрацию KeyServiceRegistrar
    resolved_form_connection_data = container.resolve(FormConnectionData)
    assert resolved_form_connection_data is not None
    assert isinstance(resolved_form_connection_data, FormConnectionData)

    resolved_formation_key = container.resolve(FormationKey)
    assert resolved_formation_key is not None
    assert isinstance(resolved_formation_key, FormationKey)

    resolved_create_key = container.resolve(CreateKey)
    assert resolved_create_key is not None
    assert isinstance(resolved_create_key, CreateKey)

    resolved_key_renewal = container.resolve(KeyRenewal)
    assert resolved_key_renewal is not None
    assert isinstance(resolved_key_renewal, KeyRenewal)

    # Проверяем регистрацию UserServiceRegistrar
    resolved_saturation_user = container.resolve(SaturationUser)
    assert resolved_saturation_user is not None
    assert isinstance(resolved_saturation_user, SaturationUser)

    resolved_trial_service = container.resolve(TrialService)
    assert resolved_trial_service is not None
    assert isinstance(resolved_trial_service, TrialService)

    resolved_delete_user = container.resolve(DeleteUser)
    assert resolved_delete_user is not None
    assert isinstance(resolved_delete_user, DeleteUser)

    # Проверяем регистрацию GiftServiceRegistrar
    resolved_checker_gift_link = container.resolve(CheckerGiftLink)
    assert resolved_checker_gift_link is not None
    assert isinstance(resolved_checker_gift_link, CheckerGiftLink)

    resolved_token_gen = container.resolve(TokenGen)
    assert resolved_token_gen is not None
    assert isinstance(resolved_token_gen, TokenGen)

    resolved_gift_link_provider = container.resolve(GiftLinkProvider)
    assert resolved_gift_link_provider is not None
    assert isinstance(resolved_gift_link_provider, GiftLinkProvider)
