import asyncpg
from datetime import datetime, timedelta, timezone
from typing import Optional
from app.core.security import generate_login_code


class LoginCodesRepo:
    async def create(
        self, conn: asyncpg.Connection, tg_id: int, ttl_hours: int
    ) -> tuple[str, datetime]:
        code = generate_login_code()
        expires_at = datetime.now(timezone.utc) + timedelta(hours=ttl_hours)
        row = await conn.fetchrow(
            "INSERT INTO login_codes (code, tg_id, expires_at) VALUES ($1, $2, $3) RETURNING code, expires_at",
            code, tg_id, expires_at,
        )
        return row["code"], row["expires_at"]

    async def consume(self, conn: asyncpg.Connection, code: str) -> Optional[asyncpg.Record]:
        """Атомарно отмечает код использованным. Защита от TOCTOU."""
        return await conn.fetchrow(
            """
            UPDATE login_codes
            SET used = TRUE
            WHERE code = $1
              AND used = FALSE
              AND expires_at > NOW()
            RETURNING *
            """,
            code.upper(),
        )
