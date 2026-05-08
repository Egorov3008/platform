import httpx
import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from httpx import HTTPStatusError
from app.core.dependencies import get_current_user, get_conn, get_backend_client, get_backend_client_no_auth
from app.core.security import set_auth_cookies, clear_auth_cookies, create_access_token, create_refresh_token, verify_telegram_data
from app.core.config import settings
from app.core.logging import get_logger
from app.core.captcha import generate_captcha, verify_captcha, CaptchaError
from app.schemas.auth import UserInfoResponse, TelegramCallbackRequest, TelegramOnlyRequest, LoginCodeRequest, CaptchaResponse
from app.services import auth as auth_service
from app.api.backend_client import WebBackendClient

router = APIRouter()
logger = get_logger(__name__)


@router.post("/login")
async def login(
    body: LoginCodeRequest,
    response: Response,
    conn: asyncpg.Connection = Depends(get_conn),
):
    access_token, refresh_token = await auth_service.login_with_code(conn, body.code)
    set_auth_cookies(response, access_token, refresh_token)
    return {"message": "ok"}


@router.post("/telegram-login")
async def telegram_login(
    request: TelegramOnlyRequest,
    response: Response,
    conn: asyncpg.Connection = Depends(get_conn),
    backend_client: WebBackendClient = Depends(get_backend_client_no_auth),
):
    """Telegram Widget login without CAPTCHA — for the code-login page bottom strip."""
    try:
        tg_data = verify_telegram_data(request.telegram_data)
        tg_id = tg_data.get("id")
        if not tg_id:
            raise HTTPException(status_code=400, detail="Invalid Telegram data: missing user ID")

        user = None
        try:
            user = await backend_client.get_user(tg_id)
        except HTTPStatusError as e:
            if e.response.status_code == 404:
                try:
                    user = await backend_client.create_user(tg_id)
                except HTTPStatusError as create_error:
                    raise HTTPException(status_code=create_error.response.status_code, detail="Failed to register user")
            else:
                raise HTTPException(status_code=503, detail="Service unavailable")

        access_token, refresh_token = await auth_service.login_via_telegram(conn, tg_id, user.is_admin)
        set_auth_cookies(response, access_token, refresh_token)
        logger.info(f"✓ Telegram login (no captcha): tg_id={tg_id}")
        return {"message": "ok", "user": {"tg_id": tg_id, "is_admin": user.is_admin}}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in telegram_login: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/captcha", response_model=CaptchaResponse)
async def get_captcha():
    return generate_captcha(settings.captcha_secret)


@router.post("/telegram-callback")
async def telegram_callback(
    request: TelegramCallbackRequest,
    response: Response,
    conn: asyncpg.Connection = Depends(get_conn),
    backend_client: WebBackendClient = Depends(get_backend_client),
):
    """
    Handle Telegram Widget authentication callback.

    For new users: auto-creates in backend
    For existing users: uses existing data

    Both paths converge to JWT generation and session storage.
    """
    try:
        # 1. Verify CAPTCHA
        logger.debug(f"Verifying CAPTCHA: token={request.captcha_token[:8]}...")
        try:
            verify_captcha(
                request.captcha_answer,
                request.captcha_timestamp,
                request.captcha_token,
                settings.captcha_secret,
            )
        except CaptchaError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        logger.debug("✓ CAPTCHA verified")

        # 2. Verify Telegram data and extract tg_id
        logger.debug("Verifying Telegram signature...")
        tg_data = verify_telegram_data(request.telegram_data)
        tg_id = tg_data.get("id")

        if not tg_id:
            logger.error("No tg_id in verified Telegram data")
            raise HTTPException(
                status_code=400,
                detail="Invalid Telegram data: missing user ID"
            )

        logger.debug(f"✓ Telegram signature verified, tg_id={tg_id}")

        # 3. [NEW] Check if user exists in backend
        user = None
        try:
            logger.debug(f"Checking if user exists: tg_id={tg_id}")
            user = await backend_client.get_user(tg_id)
            logger.info(f"✓ Existing user login: tg_id={tg_id}")
        except HTTPStatusError as e:
            if e.response.status_code == 404:
                # New user: auto-create in backend
                logger.info(f"New user detected, creating: tg_id={tg_id}")
                try:
                    user = await backend_client.create_user(tg_id)
                    logger.info(f"✓ New user created: tg_id={tg_id}")
                except HTTPStatusError as create_error:
                    logger.error(
                        f"Failed to create user: tg_id={tg_id}, "
                        f"status={create_error.response.status_code}",
                        exc_info=True
                    )
                    raise HTTPException(
                        status_code=create_error.response.status_code,
                        detail="Failed to register user"
                    )
            else:
                # Backend error (5xx, network, etc.)
                logger.error(
                    f"Backend error on user check: tg_id={tg_id}, "
                    f"status={e.response.status_code}",
                    exc_info=True
                )
                raise HTTPException(
                    status_code=503,
                    detail="Service unavailable"
                )

        # 4. Generate JWT and save session via auth service
        logger.debug(f"Generating JWT: tg_id={tg_id}, is_admin={user.is_admin}")
        access_token, refresh_token = await auth_service.login_via_telegram(
            conn, tg_id, user.is_admin
        )
        logger.debug("✓ JWT tokens generated and session saved")

        # 5. Set cookies and return response
        set_auth_cookies(response, access_token, refresh_token)
        logger.info(f"✓ Login successful: tg_id={tg_id}")
        return {"message": "ok", "user": {"tg_id": tg_id, "is_admin": user.is_admin}}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in telegram_callback: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )


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
