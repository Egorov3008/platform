from typing import Optional
import asyncpg


class LoginCodesRepo:
    async def consume(self, conn: asyncpg.Connection, code: str) -> Optional[asyncpg.Record]:
        """Atomically marks code used. Returns record if valid, None if expired/used/not found."""
        return await conn.fetchrow(
            """UPDATE login_codes
               SET used = TRUE
               WHERE code = $1 AND used = FALSE AND expires_at > NOW()
               RETURNING *""",
            code.upper(),
        )
