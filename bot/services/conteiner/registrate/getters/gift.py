import punq
from punq import Container

from dialogs.windows.getters.gift.main import MainGetter
from dialogs.windows.widgets.keybord.gift.main import GiftMainKeyboard
from dialogs.windows.widgets.message.gift.main import GiftMainMessage
from services.conteiner.protocol import ContainerProtocol
from services.core.data.service import ServiceDataModel
from services.core.gift.repositories.gen_url import GiftUrlGenerator


class GiftRegistrar(ContainerProtocol):
    def register_dependencies(self, container: Container) -> None:
        def build_gift_url_generator():
            return GiftUrlGenerator()

        def build_main_getter():
            return MainGetter(
                model_data=container.resolve(ServiceDataModel),
                url_service=container.resolve(GiftUrlGenerator),
            )

        container.register(
            GiftUrlGenerator,
            factory=build_gift_url_generator,
            scope=punq.Scope.singleton,
        )
        container.register(
            MainGetter, factory=build_main_getter, scope=punq.Scope.singleton
        )
        container.register(
            GiftMainMessage,
            factory=lambda: GiftMainMessage(),
            scope=punq.Scope.singleton,
        )
        container.register(
            GiftMainKeyboard,
            factory=lambda: GiftMainKeyboard(),
            scope=punq.Scope.singleton,
        )
