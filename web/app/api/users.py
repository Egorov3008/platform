"""User info endpoint — returns current user's data from backend."""

from fastapi import APIRouter, Depends, HTTPException, status
from app.api.backend_client import WebBackendClient
from app.core.dependencies import get_backend_client, get_current_user
from app.schemas.users import UserResponse
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/me", response_model=UserResponse)
async def get_me(
    backend: WebBackendClient = Depends(get_backend_client),
    current_user: dict = Depends(get_current_user),
):
    tg_id = current_user.get("tg_id")
    if not tg_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Telegram account required",
        )
    try:
        return await backend.get_user(tg_id)
    except Exception as e:
        logger.error("GET /users/me: ошибка", extra={"error": str(e), "tg_id": tg_id})
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Backend error")
