"""
Интеграционные тесты DI-контейнера (services/container/app.py).

Проверяет:
- Инициализацию контейнера через create_container() с замоканным пулом БД
- Вызов всех регистраторов без ошибок
- Синглтон-поведение сервисов (CacheService, ServiceDataModel)
- Разрешение зависимостей (resolve) для ключевых сервисов
"""

import asyncpg
import pytest
from unittest.mock import AsyncMock, patch
from punq import Container

from services.container import create_container
from services.container.registrate.core import (
    CacheRegistrar,
    CoreServiceRegistrar,
    GiftServiceRegistrar,
    KeyServiceRegistrar,
    TariffServiceRegistrar,
    UserServiceRegistrar,
    RegistrationRegistrar,
)
from services.container.registrate.scenario import ScenarioKeyRegistrar
from services.container.registrate.getters import (
    ProfileRegistrar,
    GiftRegistrar,
    PaymentRegistrar,
    TariffGetterRegistration,
    KeysRegistrar,
    RegisterRegistrar,
    InstructionRegistrar,
)

from services.cache.service import CacheService
from services.cache.storage import CacheStorage
from services.core.data.service import ServiceDataModel
from database.service import DataService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_pool() -> AsyncMock:
    """Создаёт AsyncMock, достаточный для регистрации asyncpg.Pool в контейнере."""
    pool = AsyncMock(spec=asyncpg.Pool)
    pool.acquire = AsyncMock(return_value=AsyncMock())
    return pool


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_pool() -> AsyncMock:
    """Мок пула соединений — не обращается к реальной БД."""
    return _make_mock_pool()


@pytest.fixture
async def full_container(mock_pool: AsyncMock) -> Container:
    """
    Контейнер, созданный через create_container() с замоканным create_db_pool.
    Соответствует тому, что используется в продакшн-коде при старте бота.
    """
    with patch("services.container.create_db_pool", return_value=mock_pool):
        container = await create_container()
    return container


@pytest.fixture
def bare_container(mock_pool: AsyncMock) -> Container:
    """
    Чистый контейнер с минимальными базовыми зависимостями.
    Используется для проверки отдельных регистраторов без полной инициализации.
    """
    container = Container()
    container.register(asyncpg.Pool, instance=mock_pool)
    container.register(DataService, scope="singleton")
    container.register(CacheStorage, scope="singleton")

    cache_storage = container.resolve(CacheStorage)
    cache_service = CacheService(storage=cache_storage)
    container.register(CacheService, instance=cache_service)

    data_service = container.resolve(DataService)
    sdm = ServiceDataModel(cache_service=cache_service, data_service=data_service)
    container.register(ServiceDataModel, instance=sdm)

    return container


# ---------------------------------------------------------------------------
# TestDIContainerRegistration
# ---------------------------------------------------------------------------


class TestDIContainerRegistration:
    """Проверяет успешную инициализацию контейнера и вызов регистраторов."""

    async def test_container_initialized_without_error(
        self, mock_pool: AsyncMock
    ) -> None:
        """create_container() должен возвращать Container без исключений."""
        with patch("services.container.create_db_pool", return_value=mock_pool):
            container = await create_container()

        assert isinstance(container, Container)

    async def test_asyncpg_pool_registered(self, full_container: Container) -> None:
        """asyncpg.Pool должен быть зарегистрирован и разрешаться в контейнере."""
        pool = full_container.resolve(asyncpg.Pool)
        assert pool is not None

    async def test_data_service_registered(self, full_container: Container) -> None:
        """DataService регистрируется через CoreServiceRegistrar."""
        service = full_container.resolve(DataService)
        assert isinstance(service, DataService)

    async def test_cache_storage_registered(self, full_container: Container) -> None:
        """CacheStorage регистрируется через CacheRegistrar."""
        storage = full_container.resolve(CacheStorage)
        assert isinstance(storage, CacheStorage)

    async def test_cache_service_registered(self, full_container: Container) -> None:
        """CacheService регистрируется через CacheRegistrar."""
        service = full_container.resolve(CacheService)
        assert isinstance(service, CacheService)

    async def test_service_data_model_registered(
        self, full_container: Container
    ) -> None:
        """ServiceDataModel регистрируется через CoreServiceRegistrar."""
        sdm = full_container.resolve(ServiceDataModel)
        assert isinstance(sdm, ServiceDataModel)

    async def test_cache_registrar_runs_without_error(
        self, bare_container: Container
    ) -> None:
        """CacheRegistrar.register_dependencies() не должен бросать исключений."""
        CacheRegistrar().register_dependencies(bare_container)

    async def test_core_service_registrar_runs_without_error(
        self, bare_container: Container
    ) -> None:
        """CoreServiceRegistrar.register_dependencies() не должен бросать исключений."""
        CoreServiceRegistrar().register_dependencies(bare_container)

    async def test_key_service_registrar_runs_without_error(
        self, bare_container: Container
    ) -> None:
        """KeyServiceRegistrar.register_dependencies() — все ключевые сервисы регистрируются."""
        # KeyServiceRegistrar зависит от XUISession через CoreServiceRegistrar
        CoreServiceRegistrar().register_dependencies(bare_container)
        KeyServiceRegistrar().register_dependencies(bare_container)

    async def test_user_service_registrar_runs_without_error(
        self, bare_container: Container
    ) -> None:
        """UserServiceRegistrar.register_dependencies() не бросает исключений."""
        CoreServiceRegistrar().register_dependencies(bare_container)
        UserServiceRegistrar().register_dependencies(bare_container)

    async def test_gift_service_registrar_runs_without_error(
        self, bare_container: Container
    ) -> None:
        """GiftServiceRegistrar.register_dependencies() не бросает исключений."""
        CoreServiceRegistrar().register_dependencies(bare_container)
        GiftServiceRegistrar().register_dependencies(bare_container)

    async def test_tariff_service_registrar_runs_without_error(
        self, bare_container: Container
    ) -> None:
        """TariffServiceRegistrar.register_dependencies() не бросает исключений."""
        CoreServiceRegistrar().register_dependencies(bare_container)
        TariffServiceRegistrar().register_dependencies(bare_container)

    async def test_registration_registrar_runs_without_error(
        self, bare_container: Container
    ) -> None:
        """RegistrationRegistrar.register_dependencies() не бросает исключений."""
        CoreServiceRegistrar().register_dependencies(bare_container)
        RegistrationRegistrar().register_dependencies(bare_container)

    async def test_scenario_key_registrar_runs_without_error(
        self, bare_container: Container
    ) -> None:
        """ScenarioKeyRegistrar требует CreateKey, GiftLinkProvider, TrialService, asyncpg.Pool."""
        CoreServiceRegistrar().register_dependencies(bare_container)
        GiftServiceRegistrar().register_dependencies(bare_container)
        KeyServiceRegistrar().register_dependencies(bare_container)
        UserServiceRegistrar().register_dependencies(bare_container)
        ScenarioKeyRegistrar().register_dependencies(bare_container)

    async def test_getter_profile_registrar_runs_without_error(
        self, bare_container: Container
    ) -> None:
        """ProfileRegistrar зависит от CheckerGiftLink, CheckedUser, CreateFerstKeyScenario."""
        CoreServiceRegistrar().register_dependencies(bare_container)
        GiftServiceRegistrar().register_dependencies(bare_container)
        KeyServiceRegistrar().register_dependencies(bare_container)
        UserServiceRegistrar().register_dependencies(bare_container)
        TariffServiceRegistrar().register_dependencies(bare_container)
        ScenarioKeyRegistrar().register_dependencies(bare_container)
        RegistrationRegistrar().register_dependencies(bare_container)
        ProfileRegistrar().register_dependencies(bare_container)

    async def test_getter_gift_registrar_runs_without_error(
        self, bare_container: Container
    ) -> None:
        """GiftRegistrar (getter) зависит от ServiceDataModel."""
        CoreServiceRegistrar().register_dependencies(bare_container)
        GiftRegistrar().register_dependencies(bare_container)

    async def test_getter_register_registrar_runs_without_error(
        self, bare_container: Container
    ) -> None:
        """RegisterRegistrar регистрирует UI-компоненты окна регистрации."""
        RegisterRegistrar().register_dependencies(bare_container)

    async def test_getter_instruction_registrar_runs_without_error(
        self, bare_container: Container
    ) -> None:
        """InstructionRegistrar зависит от ServiceDataModel и CreateFerstKeyScenario."""
        CoreServiceRegistrar().register_dependencies(bare_container)
        GiftServiceRegistrar().register_dependencies(bare_container)
        KeyServiceRegistrar().register_dependencies(bare_container)
        UserServiceRegistrar().register_dependencies(bare_container)
        TariffServiceRegistrar().register_dependencies(bare_container)
        ScenarioKeyRegistrar().register_dependencies(bare_container)
        InstructionRegistrar().register_dependencies(bare_container)

    async def test_getter_tariff_registrar_runs_without_error(
        self, bare_container: Container
    ) -> None:
        """TariffGetterRegistration зависит от TariffData, Pricing, CacheService, ServiceDataModel."""
        CoreServiceRegistrar().register_dependencies(bare_container)
        TariffServiceRegistrar().register_dependencies(bare_container)
        TariffGetterRegistration().register_dependencies(bare_container)

    async def test_getter_keys_registrar_runs_without_error(
        self, bare_container: Container
    ) -> None:
        """KeysRegistrar регистрирует все UI-компоненты раздела ключей."""
        CoreServiceRegistrar().register_dependencies(bare_container)
        GiftServiceRegistrar().register_dependencies(bare_container)
        KeyServiceRegistrar().register_dependencies(bare_container)
        UserServiceRegistrar().register_dependencies(bare_container)
        TariffServiceRegistrar().register_dependencies(bare_container)
        ScenarioKeyRegistrar().register_dependencies(bare_container)
        KeysRegistrar().register_dependencies(bare_container)

    async def test_getter_payment_registrar_runs_without_error(
        self, bare_container: Container
    ) -> None:
        """PaymentRegistrar (getter) зависит от YooKassService, ServiceDataModel, CacheService."""
        CoreServiceRegistrar().register_dependencies(bare_container)
        PaymentRegistrar().register_dependencies(bare_container)


# ---------------------------------------------------------------------------
# TestDIContainerSingletons
# ---------------------------------------------------------------------------


class TestDIContainerSingletons:
    """Проверяет singleton-поведение сервисов в контейнере."""

    async def test_cache_service_is_singleton(self, full_container: Container) -> None:
        """Два вызова resolve(CacheService) должны вернуть один и тот же объект."""
        service_a = full_container.resolve(CacheService)
        service_b = full_container.resolve(CacheService)
        assert service_a is service_b

    async def test_service_data_model_is_singleton(
        self, full_container: Container
    ) -> None:
        """Два вызова resolve(ServiceDataModel) должны вернуть один и тот же объект."""
        sdm_a = full_container.resolve(ServiceDataModel)
        sdm_b = full_container.resolve(ServiceDataModel)
        assert sdm_a is sdm_b

    async def test_cache_storage_is_singleton(self, full_container: Container) -> None:
        """CacheStorage зарегистрирован как singleton."""
        storage_a = full_container.resolve(CacheStorage)
        storage_b = full_container.resolve(CacheStorage)
        assert storage_a is storage_b

    async def test_data_service_is_singleton(self, full_container: Container) -> None:
        """DataService зарегистрирован как singleton."""
        ds_a = full_container.resolve(DataService)
        ds_b = full_container.resolve(DataService)
        assert ds_a is ds_b

    async def test_asyncpg_pool_is_singleton(
        self, full_container: Container, mock_pool: AsyncMock
    ) -> None:
        """asyncpg.Pool зарегистрирован как instance — всегда возвращает один объект."""
        pool_a = full_container.resolve(asyncpg.Pool)
        pool_b = full_container.resolve(asyncpg.Pool)
        assert pool_a is pool_b
        assert pool_a is mock_pool

    async def test_cache_service_holds_real_storage(
        self, full_container: Container
    ) -> None:
        """CacheService должен содержать тот же CacheStorage, что и контейнер."""
        cache_service = full_container.resolve(CacheService)
        storage = full_container.resolve(CacheStorage)
        assert cache_service.storage is storage

    async def test_service_data_model_holds_cache_service(
        self, full_container: Container
    ) -> None:
        """ServiceDataModel должен ссылаться на тот же CacheService из контейнера."""
        sdm = full_container.resolve(ServiceDataModel)
        cache_service = full_container.resolve(CacheService)
        assert sdm.cache_service is cache_service

    async def test_service_data_model_holds_data_service(
        self, full_container: Container
    ) -> None:
        """ServiceDataModel должен ссылаться на тот же DataService из контейнера."""
        sdm = full_container.resolve(ServiceDataModel)
        data_service = full_container.resolve(DataService)
        assert sdm.data_service is data_service


# ---------------------------------------------------------------------------
# TestDIContainerDependencies
# ---------------------------------------------------------------------------


class TestDIContainerDependencies:
    """Проверяет разрешение зависимостей для основных сервисов."""

    async def test_service_data_model_has_entity_attributes(
        self, full_container: Container
    ) -> None:
        """ServiceDataModel должен иметь все восемь атрибутов-сущностей."""
        sdm = full_container.resolve(ServiceDataModel)
        for attr in (
            "users",
            "keys",
            "servers",
            "inbounds",
            "payments",
            "gifts",
            "tariffs",
            "stocks",
        ):
            assert hasattr(sdm, attr), f"ServiceDataModel не содержит атрибут '{attr}'"

    async def test_cache_service_has_entity_caches(
        self, full_container: Container
    ) -> None:
        """CacheService должен иметь все восемь атрибутов кеша."""
        cache_service = full_container.resolve(CacheService)
        for attr in (
            "users",
            "keys",
            "servers",
            "tariffs",
            "gifts",
            "inbounds",
            "payments",
            "stocks",
        ):
            assert hasattr(cache_service, attr), (
                f"CacheService не содержит кеш '{attr}'"
            )

    async def test_pool_is_accessible_from_container(
        self, full_container: Container, mock_pool: AsyncMock
    ) -> None:
        """asyncpg.Pool из контейнера должен совпадать с мок-пулом."""
        resolved_pool = full_container.resolve(asyncpg.Pool)
        assert resolved_pool is mock_pool

    async def test_multiple_resolves_return_consistent_types(
        self, full_container: Container
    ) -> None:
        """Повторные разрешения должны возвращать объекты одного типа."""
        sdm1 = full_container.resolve(ServiceDataModel)
        sdm2 = full_container.resolve(ServiceDataModel)
        assert type(sdm1) is type(sdm2)
        assert isinstance(sdm1, ServiceDataModel)

    async def test_create_container_calls_create_db_pool(
        self, mock_pool: AsyncMock
    ) -> None:
        """create_container() должен вызывать create_db_pool ровно один раз."""
        with patch(
            "services.container.create_db_pool", return_value=mock_pool
        ) as mock_create:
            await create_container()

        mock_create.assert_awaited_once()

    async def test_pool_registered_as_asyncpg_pool_type(
        self, full_container: Container
    ) -> None:
        """Пул должен быть зарегистрирован под типом asyncpg.Pool."""
        pool = full_container.resolve(asyncpg.Pool)
        # AsyncMock не является экземпляром asyncpg.Pool, но должен быть нашим моком
        assert pool is not None

    async def test_container_returns_same_instance_across_fixture_calls(
        self, full_container: Container
    ) -> None:
        """
        Один и тот же контейнер возвращает идентичные singleton-объекты
        при любом количестве последовательных вызовов resolve.
        """
        results = [full_container.resolve(CacheService) for _ in range(5)]
        assert all(r is results[0] for r in results), (
            "CacheService не является singleton — возвращаются разные объекты"
        )
