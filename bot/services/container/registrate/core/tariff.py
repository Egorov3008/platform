import punq

from services.container.protocol import ContainerProtocol
from punq import Container

from api.backend_client import BackendAPIClient
from services.core.price.form_price import Pricing
from services.core.price.service import PriceService
from services.core.tariff.data import TariffData
from services.core.user.utils.checked_admin import CheckedUser


class TariffServiceRegistrar(ContainerProtocol):
    def register_dependencies(self, container: Container) -> None:

        def build_tariff_data():
            return TariffData(
                backend=container.resolve(BackendAPIClient),
                checked_user=container.resolve(CheckedUser),
            )

        def build_price_service():
            return PriceService(
                pricing=container.resolve(Pricing),
                backend=container.resolve(BackendAPIClient),
            )

        container.register(Pricing, scope=punq.Scope.singleton)
        container.register(
            TariffData, factory=build_tariff_data, scope=punq.Scope.singleton
        )
        container.register(
            PriceService, factory=build_price_service, scope=punq.Scope.singleton
        )
