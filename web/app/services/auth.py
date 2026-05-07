import secrets
import asyncpg
from fastapi import HTTPException, status
from app.repositories.web_users import WebUsersRepo
from app.core.security import hash_password, create_access_token, create_refresh_token, decode_token
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

web_users_repo = WebUsersRepo()


def _is_admin(tg_id: int | None) -> bool:
    return tg_id in settings.admin_tg_ids if tg_id else False


async def refresh_tokens_from_cookie(refresh_token: str) -> tuple[str, str]:
    try:
        payload = decode_token(refresh_token)
    except ValueError:
        logger.warning("Недействительный refresh token")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    tg_id = payload.get("tg_id")
    new_payload = {"sub": payload["sub"], "tg_id": tg_id, "is_admin": _is_admin(tg_id)}
    return create_access_token(new_payload), create_refresh_token(new_payload)


async def login_via_telegram(
    conn: asyncpg.Connection, tg_id: int, is_admin: bool
) -> tuple[str, str]:
    """Аутентификация через Telegram Login Widget.

    Ищет web_users по tg_id; если не найден — создаёт нового пользователя
    с email вида ``tg_<id>@bot.local`` и случайным password_hash. Возвращает
    пару (access_token, refresh_token).
    """
    user = await web_users_repo.get_by_tg_id(conn, tg_id)
    if not user:
        user = await web_users_repo.create(
            conn,
            email=f"tg_{tg_id}@bot.local",
            password_hash=hash_password(secrets.token_hex(32)),
            tg_id=tg_id,
        )
        logger.info("Создан новый web_users через Telegram-авторизацию для tg_id=%d", tg_id)
    payload = {"sub": str(user["id"]), "tg_id": tg_id, "is_admin": is_admin}
    return create_access_token(payload), create_refresh_token(payload)
