import secrets
import asyncpg
from fastapi import HTTPException, status
from app.repositories.web_users import WebUsersRepo
from app.repositories.login_codes import LoginCodesRepo
from app.core.security import hash_password, create_access_token, create_refresh_token, decode_token
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

web_users_repo = WebUsersRepo()
login_codes_repo = LoginCodesRepo()


def _is_admin(tg_id: int | None) -> bool:
    return tg_id in settings.admin_tg_ids if tg_id else False


def _build_tokens(user_id: int, tg_id: int | None) -> dict:
    payload = {"sub": str(user_id), "tg_id": tg_id, "is_admin": _is_admin(tg_id)}
    return {
        "access_token": create_access_token(payload),
        "refresh_token": create_refresh_token(payload),
    }


async def login_with_code(conn: asyncpg.Connection, code: str) -> tuple[str, str]:
    record = await login_codes_repo.consume(conn, code)
    if not record:
        logger.warning("Недействительный или просроченный код входа")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Code invalid or expired")
    tg_id = record["tg_id"]
    user = await web_users_repo.get_by_tg_id(conn, tg_id)
    if not user:
        user = await web_users_repo.create(
            conn,
            email=f"tg_{tg_id}@bot.local",
            password_hash=hash_password(secrets.token_hex(32)),
            tg_id=tg_id,
        )
        logger.info("Создан новый web_users для tg_id=%d", tg_id)
    tokens = _build_tokens(user["id"], tg_id)
    return tokens["access_token"], tokens["refresh_token"]


async def refresh_tokens_from_cookie(refresh_token: str) -> tuple[str, str]:
    try:
        payload = decode_token(refresh_token)
    except ValueError:
        logger.warning("Недействительный refresh token")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    tg_id = payload.get("tg_id")
    new_payload = {"sub": payload["sub"], "tg_id": tg_id, "is_admin": _is_admin(tg_id)}
    return create_access_token(new_payload), create_refresh_token(new_payload)
