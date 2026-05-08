import secrets
import string
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from fastapi import Response, HTTPException
from passlib.context import CryptContext
from jose import JWTError, jwt
from app.core.config import settings
from app.schemas.auth import TelegramAuthData

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

_CODE_CHARSET = string.ascii_uppercase + string.digits


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_token(data: dict, expires_delta: timedelta) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + expires_delta
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_access_token(data: dict) -> str:
    return create_token(data, timedelta(minutes=settings.access_token_expire_minutes))


def create_refresh_token(data: dict) -> str:
    return create_token(data, timedelta(days=settings.refresh_token_expire_days))


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError as e:
        raise ValueError(f"Invalid token: {e}")


def generate_login_code() -> str:
    return "".join(secrets.choice(_CODE_CHARSET) for _ in range(8))


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    csrf_token = secrets.token_hex(32)
    response.set_cookie(
        "access_token", access_token,
        httponly=True, samesite="strict",
        max_age=settings.access_token_expire_minutes * 60,
    )
    response.set_cookie(
        "refresh_token", refresh_token,
        httponly=True, samesite="strict",
        max_age=settings.refresh_token_expire_days * 24 * 3600,
    )
    response.set_cookie(
        "csrf_token", csrf_token,
        httponly=False, samesite="strict",
        max_age=settings.refresh_token_expire_days * 24 * 3600,
    )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie("access_token", samesite="strict")
    response.delete_cookie("refresh_token", samesite="strict")
    response.delete_cookie("csrf_token", samesite="strict")


def verify_telegram_data(tg_data: TelegramAuthData) -> dict:
    """Verify Telegram Widget authentication data signature."""
    data_check_string = "\n".join(
        f"{key}={value}"
        for key, value in sorted(tg_data.dict(exclude={"hash"}).items())
    )
    secret = hashlib.sha256(settings.telegram_bot_token.encode()).digest()
    computed_hash = hmac.new(secret, data_check_string.encode(), hashlib.sha256).hexdigest()

    if computed_hash != tg_data.hash:
        raise HTTPException(status_code=400, detail="Invalid Telegram signature")

    return tg_data.dict()
