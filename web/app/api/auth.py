from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
import asyncpg
from app.core.dependencies import get_conn, get_current_user
from app.core.security import set_auth_cookies, clear_auth_cookies
from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.auth import LoginCodeRequest, UserInfoResponse
from app.services import auth as auth_service

router = APIRouter()
logger = get_logger(__name__)


@router.post("/login")
async def login(
    body: LoginCodeRequest,
    response: Response,
    conn: asyncpg.Connection = Depends(get_conn),
):
    logger.info("Попытка входа по коду")
    access_token, refresh_token = await auth_service.login_with_code(conn, body.code)
    set_auth_cookies(response, access_token, refresh_token)
    logger.info("Успешный вход по коду")
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
