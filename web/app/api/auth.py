import httpx
import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from app.core.dependencies import get_current_user, get_conn
from app.core.security import set_auth_cookies, clear_auth_cookies
from app.core.config import settings
from app.core.logging import get_logger
from app.core.captcha import generate_captcha, verify_captcha, CaptchaError
from app.schemas.auth import UserInfoResponse, TelegramCallbackRequest, CaptchaResponse
from app.services import auth as auth_service

router = APIRouter()
logger = get_logger(__name__)


@router.get("/captcha", response_model=CaptchaResponse)
async def get_captcha():
    return generate_captcha(settings.captcha_secret)


@router.post("/telegram-callback")
async def telegram_callback(
    body: TelegramCallbackRequest,
    response: Response,
    conn: asyncpg.Connection = Depends(get_conn),
):
    # 1. Проверить капчу
    try:
        verify_captcha(
            body.captcha_answer,
            body.captcha_timestamp,
            body.captcha_token,
            settings.captcha_secret,
        )
    except CaptchaError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # 2. Вызвать backend для верификации Telegram и авторегистрации
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{settings.backend_url}/api/v1/auth/telegram-login",
                json=body.telegram_data.dict(),
                headers={"X-Bot-Secret": settings.bot_secret_key},
            )
        resp.raise_for_status()
        backend_data = resp.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            raise HTTPException(status_code=401, detail="Invalid Telegram auth data")
        logger.error("Backend telegram-login error", status=e.response.status_code)
        raise HTTPException(status_code=502, detail="Auth backend error")
    except httpx.RequestError:
        logger.error("Backend unreachable during telegram-login")
        raise HTTPException(status_code=502, detail="Auth backend unreachable")

    # 3. Создать/найти web_users, выпустить JWT
    tg_id = backend_data["tg_id"]
    is_admin = backend_data["is_admin"]
    access_token, refresh_token = await auth_service.login_via_telegram(conn, tg_id, is_admin)
    set_auth_cookies(response, access_token, refresh_token)
    logger.info("Успешный вход через Telegram Widget", extra={"tg_id": tg_id})
    return {"message": "ok"}


@router.get("/me", response_model=UserInfoResponse)
async def me(current_user: dict = Depends(get_current_user)):
    return {
        "id": int(current_user["sub"]),
        "tg_id": current_user.get("tg_id"),
        "is_admin": current_user.get("is_admin", False),
    }


@router.post("/logout")
async def logout(response: Response):
    clear_auth_cookies(response)
    return {"message": "ok"}


@router.post("/refresh")
async def refresh(request: Request, response: Response):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh token")
    access_token, new_refresh_token = await auth_service.refresh_tokens_from_cookie(refresh_token)
    set_auth_cookies(response, access_token, new_refresh_token)
    return {"message": "ok"}


@router.get("/config")
async def config():
    return {"telegram_bot_username": settings.telegram_bot_username}
