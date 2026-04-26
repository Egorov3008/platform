import punq
from punq import Container

from services.conteiner.protocol import ContainerProtocol
from services.core.data.service import ServiceDataModel

# Импорты сервисов
from services.core.gift import TokenGen, GiftLinkProvider
from services.core.gift.repositories.checker import CheckerGiftLink


class GiftServiceRegistrar(ContainerProtocol):
    def register_dependencies(self, container: Container) -> None:
        def build_checking_gift():
            return CheckerGiftLink(model_data=container.resolve(ServiceDataModel))

        def build_gen_token():
            return TokenGen(model_data=container.resolve(ServiceDataModel))

        def build_gift_provider():
            return GiftLinkProvider(
                gen_token=build_gen_token(),
                model_data=container.resolve(ServiceDataModel),
            )

        container.register(
            CheckerGiftLink, factory=build_checking_gift, scope=punq.Scope.singleton
        )
        container.register(
            GiftLinkProvider, factory=build_gift_provider, scope=punq.Scope.singleton
        )
        container.register(
            TokenGen, factory=build_gen_token, scope=punq.Scope.singleton
        )
