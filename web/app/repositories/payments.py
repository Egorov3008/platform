"""Репозиторий платежей (таблица payments).

Хранит информацию о платежах, обновляет статусы и предоставляет
метрики выручки за месяц/день.
"""

import asyncpg
from typing import Optional


class PaymentsRepo:
    async def create(
        self, conn: asyncpg.Connection, payment_id: str, tg_id: int,
        amount: float, payment_type: str, number_of_months: int = 1,
        discount_percent: int = 0, status: str = "pending", referral_discount: float = 0.0
    ) -> asyncpg.Record:
        return await conn.fetchrow(
            """
            INSERT INTO payments
                (payment_id, tg_id, amount, payment_type, number_of_months, discount_percent, status, referral_discount)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING *
            """,
            payment_id, tg_id, amount, payment_type, number_of_months, discount_percent, status, referral_discount,
        )

    async def get_by_payment_id(self, conn: asyncpg.Connection, payment_id: str) -> Optional[asyncpg.Record]:
        return await conn.fetchrow("SELECT * FROM payments WHERE payment_id = $1", payment_id)

    async def update_status(self, conn: asyncpg.Connection, payment_id: str, status: str) -> None:
        await conn.execute("UPDATE payments SET status = $1 WHERE payment_id = $2", status, payment_id)

    async def revenue_month(self, conn: asyncpg.Connection) -> float:
        return float(await conn.fetchval(
            "SELECT COALESCE(SUM(amount), 0) FROM payments "
            "WHERE status = 'succeeded' AND date_trunc('month', created_at) = date_trunc('month', NOW())"
        ))

    async def revenue_today(self, conn: asyncpg.Connection) -> float:
        return float(await conn.fetchval(
            "SELECT COALESCE(SUM(amount), 0) FROM payments "
            "WHERE status = 'succeeded' AND created_at::date = CURRENT_DATE"
        ))

    async def get_by_tg_id(self, conn: asyncpg.Connection, tg_id: int,
                           limit: int = 50, offset: int = 0) -> list[asyncpg.Record]:
        return await conn.fetch(
            """
            SELECT payment_id, tg_id, amount, payment_type, status, created_at
            FROM payments
            WHERE tg_id = $1
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
            """,
            tg_id, limit, offset,
        )
