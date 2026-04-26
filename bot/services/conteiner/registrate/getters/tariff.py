import punq
from punq import Container

from dialogs.windows.getters.tariff.preview import TariffPreviewGetter
from dialogs.windows.widgets.message.tariff.preview import TariffPreviewMessage
from services.cache.service import CacheService
from services.conteiner.protocol import ContainerProtocol
from services.core.price.service import PriceService
from services.core.tariff.data import TariffData


class TariffGetterRegistration(ContainerProtocol):
    def register_dependencies(self, container: Container) -> None:
        def build_tariff_preview():
            return TariffPreviewGetter(
                tariff_display=container.resolve(TariffData),
                price_service=container.resolve(PriceService),
                cache_service=container.resolve(CacheService),
            )

        container.register(
            TariffPreviewGetter,
            factory=build_tariff_preview,
            scope=punq.Scope.singleton,
        )
        container.register(
            TariffPreviewMessage,
            factory=lambda: TariffPreviewMessage(),
            scope=punq.Scope.singleton,
        )
