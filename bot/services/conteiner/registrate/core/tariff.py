import punq

from services.conteiner.protocol import ContainerProtocol
from punq import Container

from services.core.data.service import ServiceDataModel
from services.core.price.form_price import Pricing
from services.core.price.service import PriceService
from services.core.tariff.data import TariffData
from services.core.user.utils.checked_admin import CheckedUser


class TariffServiceRegistrar(ContainerProtocol):
    def register_dependencies(self, container: Container) -> None:

        def build_tariff_data():
            return TariffData(
                model_data=container.resolve(ServiceDataModel),
                checked_user=container.resolve(CheckedUser),
            )

        def build_price_service():
            return PriceService(
                pricing=container.resolve(Pricing),
                model_data=container.resolve(ServiceDataModel),
            )

        container.register(Pricing, scope=punq.Scope.singleton)
        container.register(CheckedUser, scope=punq.Scope.transient)
        container.register(
            TariffData, factory=build_tariff_data, scope=punq.Scope.singleton
        )
        container.register(
            PriceService, factory=build_price_service, scope=punq.Scope.singleton
        )
