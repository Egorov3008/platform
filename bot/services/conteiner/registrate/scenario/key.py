import asyncpg
import punq
from punq import Container

from services.cache import CacheService
from services.conteiner.protocol import ContainerProtocol
from services.core.data.service import ServiceDataModel
from services.core.gift import GiftLinkProvider
from services.core.keys.utils.create_key import CreateKey
from services.core.user.utils.trial import TrialService
from services.scenarios.create_first_key_scenario import CreateFerstKeyScenario


class ScenarioKeyRegistrar(ContainerProtocol):
    def register_dependencies(self, container: Container) -> None:
        def build_create_first_key():
            return CreateFerstKeyScenario(
                cache=container.resolve(CacheService),
                model_data=container.resolve(ServiceDataModel),
                create_key=container.resolve(CreateKey),
                gift_service=container.resolve(GiftLinkProvider),
                trial_user=container.resolve(TrialService),
                conn=container.resolve(asyncpg.Pool),
            )

        container.register(
            CreateFerstKeyScenario,
            factory=build_create_first_key,
            scope=punq.Scope.transient,
        )
