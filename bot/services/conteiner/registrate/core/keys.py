import asyncpg
import punq
from punq import Container

from client import XUISession

from services.cache.service import CacheService
from services.conteiner.protocol import ContainerProtocol
from services.core.connect_module.repositories.form_data import FormConnectionData
from services.core.data.service import ServiceDataModel
from services.core.keys.utils.calculator import ExpiryCalculator
from services.core.keys.utils.create_key import CreateKey
from services.core.keys.utils.formtion import FormationKey
from services.core.keys.utils.updating import KeyUpdater
from services.core.keys.utils.renewal import KeyRenewal
from services.core.keys.utils.reset import KeyResetter


class KeyServiceRegistrar(ContainerProtocol):
    """Регистратор сервисов ключей"""

    def register_dependencies(self, container: Container) -> None:

        def build_form_connection_data():
            form_data = FormConnectionData(
                cache=container.resolve(CacheService),
                model_data=container.resolve(ServiceDataModel),
            )
            # Устанавливаем пул соединений для прямого доступа к БД
            pool = container.resolve(asyncpg.Pool)
            form_data.set_pool(pool)
            return form_data

        def build_formation_key():
            return FormationKey(
                cache=container.resolve(CacheService),
                connected_data=container.resolve(FormConnectionData),
                expiry=container.resolve(ExpiryCalculator),
            )

        def build_create_key():
            return CreateKey(
                model_data=container.resolve(ServiceDataModel),
                xui_session=container.resolve(XUISession),
                expiry=container.resolve(ExpiryCalculator),
                formation=container.resolve(FormationKey),
            )

        def build_key_updater():
            return KeyUpdater(expiry_calculator=container.resolve(ExpiryCalculator))

        def build_resetter():
            return KeyResetter(cache_service=container.resolve(CacheService))

        def build_renewal_key():
            return KeyRenewal(
                model_data=container.resolve(ServiceDataModel),
                xui_session=container.resolve(XUISession),
                refresh_key=container.resolve(KeyUpdater),
                resetter=container.resolve(KeyResetter),
            )

        # Регистрация фабрик

        container.register(ExpiryCalculator, scope=punq.Scope.singleton)
        container.register(
            KeyUpdater, factory=build_key_updater, scope=punq.Scope.singleton
        )
        container.register(
            KeyResetter, factory=build_resetter, scope=punq.Scope.singleton
        )
        container.register(
            FormConnectionData,
            factory=build_form_connection_data,
            scope=punq.Scope.singleton,
        )
        container.register(
            FormationKey, factory=build_formation_key, scope=punq.Scope.singleton
        )
        container.register(
            CreateKey, factory=build_create_key, scope=punq.Scope.singleton
        )
        container.register(
            KeyRenewal, factory=build_renewal_key, scope=punq.Scope.singleton
        )
