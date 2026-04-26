import asyncpg
import punq
from punq import Container

from client import XUISession
from database import DataService
from services.cache import CacheService, LoadingService
from services.conteiner.protocol import ContainerProtocol
from services.core.data.service import ServiceDataModel


class CoreServiceRegistrar(ContainerProtocol):
    """Регистратор основных сервисов"""

    def register_dependencies(self, container: Container) -> None:
        # Регистрация мока XUISession

        def build_data_service() -> DataService:
            return DataService()

        def build_data_model():
            return ServiceDataModel(
                cache_service=container.resolve(CacheService),
                data_service=container.resolve(DataService),
            )

        def build_loading_service():
            return LoadingService(
                cache=container.resolve(CacheService),
                data_service=container.resolve(DataService),
                pool=container.resolve(asyncpg.Pool),
            )

        def build_xui_session():
            return XUISession(
                model_service=container.resolve(ServiceDataModel),
                loading=container.resolve(LoadingService),
            )

        container.register(
            DataService, factory=build_data_service, scope=punq.Scope.singleton
        )
        container.register(
            ServiceDataModel, factory=build_data_model, scope=punq.Scope.singleton
        )
        container.register(
            LoadingService, factory=build_loading_service, scope=punq.Scope.singleton
        )
        container.register(
            XUISession, factory=build_xui_session, scope=punq.Scope.singleton
        )
