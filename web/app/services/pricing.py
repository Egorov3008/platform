"""Сервис расчёта цен с учётом персональных скидок и объёмных скидок.

NOTE: This service is deprecated. Pricing logic has been moved to backend.
Keeping this file temporarily for reference during migration.
"""

import asyncpg
from dataclasses import dataclass
from typing import Optional
from app.core.config import settings


@dataclass
class PriceResult:
    """Результат расчёта цены."""
    original_amount: float  # Изначальная цена тарифа
    final_amount: float  # Цена после скидок
    discount_percent: float  # Процент скидки (от оригинальной цены)
    stock_value: float  # Размер персональной скидки (фиксированная или процент)
    stock_type: Optional[str]  # "fix" или "percent" (тип персональной скидки)
    has_discount: bool  # Была ли применена скидка
    volume_discount_applied: bool  # Была ли применена объёмная скидка

    def total(self, months: int) -> float:
        """Итоговая цена за N месяцев."""
        return self.final_amount * months


# PricingService has been removed - pricing logic moved to backend API
