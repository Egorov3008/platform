"""Репозиторий для работы с реферальной системой."""

import asyncpg
from typing import Optional


class ReferralRepo:
    async def get_link_by_tg_id(self, conn: asyncpg.Connection, tg_id: int) -> Optional[asyncpg.Record]:
        """Получить реферальную ссылку по tg_id реферера."""
        return await conn.fetchrow(
            "SELECT * FROM referral_links WHERE referrer_tg_id = $1",
            tg_id,
        )

    async def get_link_by_token(self, conn: asyncpg.Connection, token: str) -> Optional[asyncpg.Record]:
        """Получить реферальную ссылку по токену."""
        return await conn.fetchrow(
            "SELECT * FROM referral_links WHERE token = $1",
            token,
        )

    async def create_link(self, conn: asyncpg.Connection, tg_id: int, token: str) -> asyncpg.Record:
        """Создать новую реферальную ссылку."""
        return await conn.fetchrow(
            """
            INSERT INTO referral_links (referrer_tg_id, token)
            VALUES ($1, $2)
            RETURNING *
            """,
            tg_id, token,
        )

    async def create_redemption(
        self,
        conn: asyncpg.Connection,
        referral_link_id: int,
        referred_tg_id: int,
    ) -> asyncpg.Record:
        """Записать погашение реферальной ссылки (новый пользователь зарегистрировался)."""
        return await conn.fetchrow(
            """
            INSERT INTO referral_redemptions (referral_link_id, referred_tg_id)
            VALUES ($1, $2)
            ON CONFLICT (referral_link_id, referred_tg_id) DO NOTHING
            RETURNING *
            """,
            referral_link_id, referred_tg_id,
        )

    async def get_redemption_by_tg_id(self, conn: asyncpg.Connection, referred_tg_id: int) -> Optional[asyncpg.Record]:
        """Получить данные о том, через какую реферальную ссылку зарегистрировался пользователь."""
        return await conn.fetchrow(
            """
            SELECT rr.*, rl.referrer_tg_id
            FROM referral_redemptions rr
            JOIN referral_links rl ON rr.referral_link_id = rl.id
            WHERE rr.referred_tg_id = $1
            """,
            referred_tg_id,
        )

    async def create_reward(
        self,
        conn: asyncpg.Connection,
        referrer_tg_id: int,
        reward_type: str,
        reward_value: float,
    ) -> asyncpg.Record:
        """Записать выплату бонуса рефереру."""
        return await conn.fetchrow(
            """
            INSERT INTO referral_rewards (referrer_tg_id, reward_type, reward_value)
            VALUES ($1, $2, $3)
            RETURNING *
            """,
            referrer_tg_id, reward_type, reward_value,
        )

    async def count_referrals(self, conn: asyncpg.Connection, referrer_tg_id: int) -> int:
        """Получить количество успешно привлечённых пользователей."""
        return await conn.fetchval(
            """
            SELECT COUNT(*) FROM referral_redemptions rr
            JOIN referral_links rl ON rr.referral_link_id = rl.id
            WHERE rl.referrer_tg_id = $1
            """,
            referrer_tg_id,
        )

    async def sum_referral_rewards(self, conn: asyncpg.Connection, referrer_tg_id: int) -> float:
        """Получить общую сумму полученных бонусов."""
        total = await conn.fetchval(
            """
            SELECT COALESCE(SUM(CAST(reward_value AS DECIMAL)), 0)
            FROM referral_rewards
            WHERE referrer_tg_id = $1
            """,
            referrer_tg_id,
        )
        return float(total) if total else 0.0
