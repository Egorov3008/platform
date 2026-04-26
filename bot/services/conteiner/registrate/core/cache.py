import asyncpg
import punq
from punq import Container

from database.service import DataService
from middlewares.cache_middleware import CacheMiddleware
from services.cache.loader import LoadingService
from services.cache.service import CacheService
from services.cache.storage import CacheStorage
from services.conteiner.protocol import ContainerProtocol


class CacheRegistrar(ContainerProtocol):
    """
    Регистратор зависимостей для кеширования.
    Регистрирует:
    - CacheStorage (singleton)
    - CacheService (singleton)
    - CacheMiddleware (factory)
    """

    def register_dependencies(self, container: Container) -> None:
        # Регистрируем хранилище

        # Регистрируем основной сервис кеширования
        def build_cache_service() -> CacheService:
            storage = container.resolve(CacheStorage)
            return CacheService(storage=storage)

        def build_cache_loading_service() -> LoadingService:
            return LoadingService(
                cache=container.resolve(CacheService),
                data_service=container.resolve(DataService),
                pool=container.resolve(asyncpg.Pool),
            )

        container.register(CacheStorage, scope=punq.Scope.singleton)
        container.register(
            CacheService, factory=build_cache_service, scope=punq.Scope.singleton
        )
        container.register(
            LoadingService,
            factory=build_cache_loading_service,
            scope=punq.Scope.singleton,
        )

        # Регистрируем мидлварь
        def build_cache_middleware() -> CacheMiddleware:
            return CacheMiddleware(cache_service=container.resolve(CacheService))

        container.register(CacheMiddleware, factory=build_cache_middleware)
