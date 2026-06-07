"""
DI регистрация сервисов сегментации ключей.
"""

from punq import Container

from services.core.keys.segmentation import KeySegmentationService
from services.core.keys.admin_report import KeyAdminReport


def register_key_segmentation(container: Container) -> None:
    """Регистрировать сервисы сегментации ключей в DI контейнере."""

    # KeySegmentationService — высокоуровневый API
    container.register(
        KeySegmentationService,
        factory=lambda: KeySegmentationService(),
    )

    # KeyAdminReport — генератор отчётов
    container.register(
        KeyAdminReport,
        factory=lambda: KeyAdminReport(),
    )
