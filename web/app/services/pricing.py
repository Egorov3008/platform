"""Сервис расчёта цен с учётом персональных скидок и объёмных скидок."""

import asyncpg
from dataclasses import dataclass
from typing import Optional
from app.repositories.tariffs import TariffsRepo
from app.repositories.stocks import StocksRepo
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


class PricingService:
    def __init__(self, tariffs_repo: TariffsRepo, stocks_repo: StocksRepo):
        self.tariffs_repo = tariffs_repo
        self.stocks_repo = stocks_repo

    async def calculate_price(
        self,
        conn: asyncpg.Connection,
        tg_id: int,
        tariff_id: int,
        months: int,
    ) -> PriceResult:
        """
        Рассчитать цену с учётом:
        1. Персональной скидки пользователя (если есть)
        2. Объёмной скидки за многомесячную подписку (2-6 месяцев)
        """
        # 1. Получить тариф
        tariff = await self.tariffs_repo.get_by_id(conn, tariff_id)
        if not tariff:
            raise ValueError(f"Tariff {tariff_id} not found")

        original_amount = float(tariff["amount"])
        final_amount = original_amount

        # 2. Получить персональную скидку пользователя (если есть)
        stock = await self.stocks_repo.get_by_tg_id(conn, tg_id)
        discount_percent = 0.0
        stock_value = 0.0
        stock_type = None
        has_discount = False

        if stock:
            stock_type = stock["stock_type"]
            stock_value = float(stock["value"])

            if stock_type == "fix":
                # Фиксированная скидка (в валюте)
                final_amount = max(0, final_amount - stock_value)
            elif stock_type == "percent":
                # Процентная скидка
                final_amount = final_amount * (1 - stock_value / 100)
                discount_percent = stock_value

            has_discount = True

        # 3. Применить объёмную скидку за многомесячную подписку
        volume_discount_applied = False
        if 2 <= months <= 6:
            # 3% скидка за многомесячное подписание
            volume_discount = settings.volume_discount_percent
            final_amount = final_amount * (1 - volume_discount)
            discount_percent += volume_discount
            volume_discount_applied = True

        # Итоговый процент скидки от оригинальной цены
        final_discount_percent = (original_amount - final_amount) / original_amount * 100 if original_amount > 0 else 0

        return PriceResult(
            original_amount=original_amount,
            final_amount=max(0, final_amount),
            discount_percent=min(100, final_discount_percent),
            stock_value=stock_value,
            stock_type=stock_type,
            has_discount=has_discount,
            volume_discount_applied=volume_discount_applied,
        )

    async def calculate_batch(
        self,
        conn: asyncpg.Connection,
        tg_id: int,
        months: int,
    ) -> dict[int, PriceResult]:
        """Рассчитать цены для всех тарифов (для вывода каталога)."""
        tariffs = await self.tariffs_repo.get_all(conn)
        return {
            tariff["id"]: await self.calculate_price(conn, tg_id, tariff["id"], months)
            for tariff in tariffs
        }
