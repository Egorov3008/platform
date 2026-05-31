from typing import List

from api.backend_client import BackendAPIClient
from models import Tariff
from config import AVAILABLE_RATES_LIST


class TariffData:
    """Класс для отображения тарифов через Backend API."""

    def __init__(self, backend: BackendAPIClient, checked_user):
        self.backend = backend
        self.checked_user = checked_user

    async def get_tariffs(self) -> List[Tariff]:
        """Возвращает список тарифов."""
        tariffs = await self.backend.admin_list_tariffs()
        return [
            Tariff.from_dict(t) for t in tariffs
            if t.get("id") in AVAILABLE_RATES_LIST
        ]

    async def get(self, user_id: int) -> List[Tariff]:
        tariffs = await self.backend.admin_list_tariffs()
        models = [Tariff.from_dict(t) for t in tariffs]
        if not self.checked_user.check(user_id):
            models = [
                tariff for tariff in models if tariff.id in AVAILABLE_RATES_LIST
            ]
        if not models:
            raise AttributeError("Тарифы не найдены")
        return models
