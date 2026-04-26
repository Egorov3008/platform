"""Сервис управления реферальной системой."""

import asyncpg
import secrets
from app.repositories.referral import ReferralRepo
from app.repositories.users import UsersRepo
from app.core.config import settings


class ReferralService:
    def __init__(self, referral_repo: ReferralRepo, users_repo: UsersRepo):
        self.referral_repo = referral_repo
        self.users_repo = users_repo

    async def get_or_create_link(self, conn: asyncpg.Connection, tg_id: int) -> str:
        """
        Получить или создать реферальную ссылку пользователя.
        Возвращает URL для поделения с друзьями.
        """
        link = await self.referral_repo.get_link_by_tg_id(conn, tg_id)

        if not link:
            # Генерируем уникальный токен (12 символов hex)
            token = self._generate_token()
            link = await self.referral_repo.create_link(conn, tg_id, token)

        token = link["token"]
        bot_username = settings.telegram_bot_username
        return f"https://t.me/{bot_username}?start={token}"

    async def process_redemption(
        self,
        conn: asyncpg.Connection,
        referred_tg_id: int,
        token: str,
    ) -> bool:
        """
        Обработать погашение реферальной ссылки (новый пользователь зарегистрировался через ссылку).
        Устанавливает user.referral_id на ID реферера.
        """
        link = await self.referral_repo.get_link_by_token(conn, token)
        if not link:
            return False

        # Создать запись о погашении
        await self.referral_repo.create_redemption(conn, link["id"], referred_tg_id)

        # Установить referral_id для нового пользователя
        user = await self.users_repo.get_by_tg_id(conn, referred_tg_id)
        if user and not user["referral_id"]:
            await conn.execute(
                "UPDATE users SET referral_id = $1 WHERE tg_id = $2",
                link["referrer_tg_id"],
                referred_tg_id,
            )

        return True

    async def process_referral_bonus(
        self,
        conn: asyncpg.Connection,
        referred_tg_id: int,
        payment_amount: float,
    ) -> None:
        """
        Обработать выплату бонуса рефереру после успешного платежа.

        Алгоритм:
        1. Получить referral_id пользователя (кто его пригласил)
        2. Проверить, что бонус ещё не был выплачен (check_referral == False)
        3. Вычислить 10% от payment_amount
        4. Добавить бонус на счёт рефереры
        5. Создать запись о награде
        6. Установить check_referral = True
        """
        user = await self.users_repo.get_by_tg_id(conn, referred_tg_id)
        if not user:
            return

        # Если у пользователя нет реферера или бонус уже выплачен
        if not user["referral_id"] or user["check_referral"]:
            return

        referrer_tg_id = user["referral_id"]
        bonus_amount = payment_amount * settings.referral_bonus_percent

        # Добавить бонус на счёт рефереры
        await self.users_repo.update_balance(conn, referrer_tg_id, bonus_amount)

        # Записать награду
        await self.referral_repo.create_reward(
            conn,
            referrer_tg_id,
            "referral_bonus",
            bonus_amount,
        )

        # Отметить, что бонус выплачен (только один раз за первый платёж)
        await conn.execute(
            "UPDATE users SET check_referral = true WHERE tg_id = $1",
            referred_tg_id,
        )

    @staticmethod
    def _generate_token() -> str:
        """Генерировать уникальный токен (12 символов hex, ~48 бит энтропии)."""
        return secrets.token_hex(6)  # 6 bytes = 12 hex chars
