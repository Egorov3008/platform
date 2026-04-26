"""Pydantic-схема тарифного плана.

Описывает структуру тарифа: название, стоимость, лимиты IP и трафика,
период действия.
"""

from pydantic import BaseModel
from typing import Optional


class TariffResponse(BaseModel):
    id: int
    name_tariff: str
    amount: float
    description: Optional[str] = None
    limit_ip: int
    period: int
    traffic_limit: float
