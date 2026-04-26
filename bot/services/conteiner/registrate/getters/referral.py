import punq
from punq import Container

from dialogs.windows.getters.referral.main import ReferralMainGetter
from dialogs.windows.widgets.keybord.referral.main import ReferralMainKeyboard
from dialogs.windows.widgets.message.referral.main import ReferralMainMessage
from services.conteiner.protocol import ContainerProtocol
from services.core.data.service import ServiceDataModel
from services.core.referral.link_generator import ReferralLinkGenerator


class ReferralRegistrar(ContainerProtocol):
    def register_dependencies(self, container: Container) -> None:
        def build_referral_getter():
            return ReferralMainGetter(
                model_data=container.resolve(ServiceDataModel),
                link_generator=container.resolve(ReferralLinkGenerator),
            )

        def build_referral_keyboard():
            return ReferralMainKeyboard(
                link_generator=container.resolve(ReferralLinkGenerator),
            )

        container.register(
            ReferralMainGetter,
            factory=build_referral_getter,
            scope=punq.Scope.singleton,
        )
        container.register(
            ReferralMainMessage,
            factory=lambda: ReferralMainMessage(),
            scope=punq.Scope.singleton,
        )
        container.register(
            ReferralMainKeyboard,
            factory=build_referral_keyboard,
            scope=punq.Scope.singleton,
        )
