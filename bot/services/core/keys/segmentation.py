"""
Сервис для работы с сегментацией ключей.

Предоставляет удобный интерфейс для фильтрации и анализа ключей
по различным критериям (истечение, активность, использование и т.д.)
"""

from datetime import datetime, timezone
from typing import List, Dict

from models import Key
from logger import logger


class KeySegmentationService:
    """
    Сервис для сегментации и анализа ключей.

    Работает только с in-memory списком Key (полученных из backend API).
    """

    def __init__(self):
        pass

    @staticmethod
    def _now_ms() -> int:
        return int(datetime.now(timezone.utc).timestamp() * 1000)

    async def segment_keys(self, keys: List[Key]) -> Dict[str, List[Key]]:
        """Распределить ключи по сегментам."""
        return {
            "active": await self.get_active(keys),
            "trial": await self.get_trial(keys),
            "expiring_24h": await self.get_expiring_24h(keys),
            "expiring_7d": await self.get_expiring_7d(keys),
            "expiring_30d": await self.get_expiring_30d(keys),
            "unused": await self.get_unused(keys),
            "expired": await self.get_expired(keys),
            "all": keys,
        }

    async def get_expiring_24h(self, keys: List[Key]) -> List[Key]:
        """Получить ключи, истекающие в ближайшие 24 часа."""
        now_ms = self._now_ms()
        threshold_24h = now_ms + 24 * 3600 * 1000
        return [
            key for key in keys
            if now_ms < key.expiry_time <= threshold_24h
        ]

    async def get_expired(self, keys: List[Key]) -> List[Key]:
        """Получить истёкшие ключи."""
        now_ms = self._now_ms()
        return [key for key in keys if key.expiry_time < now_ms]

    async def get_active(self, keys: List[Key]) -> List[Key]:
        """Получить активные ключи (не истёкшие)."""
        now_ms = self._now_ms()
        return [key for key in keys if key.expiry_time >= now_ms]

    async def get_trial(self, keys: List[Key]) -> List[Key]:
        """Получить trial ключи (tariff_id == 10)."""
        return [key for key in keys if key.tariff_id == 10]

    async def get_unused(self, keys: List[Key]) -> List[Key]:
        """Получить неиспользуемые ключи (0 байт трафика)."""
        return [key for key in keys if getattr(key, "used_traffic", 0) == 0]

    async def get_expiring_7d(self, keys: List[Key]) -> List[Key]:
        """Получить ключи, истекающие в ближайшие 7 дней."""
        now_ms = self._now_ms()
        threshold_7d = now_ms + 7 * 24 * 3600 * 1000
        return [
            key for key in keys
            if now_ms < key.expiry_time <= threshold_7d
        ]

    async def get_expiring_30d(self, keys: List[Key]) -> List[Key]:
        """Получить ключи, истекающие в ближайшие 30 дней."""
        now_ms = self._now_ms()
        threshold_30d = now_ms + 30 * 24 * 3600 * 1000
        return [
            key for key in keys
            if now_ms < key.expiry_time <= threshold_30d
        ]

    async def filter_by_name(self, keys: List[Key], name: str) -> List[Key]:
        """Фильтровать ключи по имени сегмента."""
        mapping = {
            "expiring_24h": self.get_expiring_24h,
            "expiring_7d": self.get_expiring_7d,
            "expiring_30d": self.get_expiring_30d,
            "expired": self.get_expired,
            "active": self.get_active,
            "trial": self.get_trial,
            "unused": self.get_unused,
            "all": lambda k: k,
        }
        handler = mapping.get(name)
        if handler:
            return await handler(keys)
        return keys
