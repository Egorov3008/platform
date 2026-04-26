from fastapi import APIRouter, Depends, Header, HTTPException, status
import asyncpg
from app.core.dependencies import get_conn
from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.auth import GenerateCodeRequest, GenerateCodeResponse
from app.schemas.bot import (
    UserRegisterRequest, UserResponse, PriceResult, TrialKeyRequest,
    KeyResponse, BotPaymentRequest, BotPaymentResponse, ReferralLinkResponse,
    ReferralStatsResponse
)
from app.repositories.login_codes import LoginCodesRepo
from app.repositories.users import UsersRepo

router = APIRouter()
logger = get_logger(__name__)

login_codes_repo = LoginCodesRepo()
users_repo = UsersRepo()


def _verify_bot_secret(x_bot_secret: str | None = Header(default=None)):
    if not x_bot_secret or x_bot_secret != settings.bot_secret_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid bot secret")


@router.post("/auth/generate-code", response_model=GenerateCodeResponse)
async def generate_code(
    body: GenerateCodeRequest,
    conn: asyncpg.Connection = Depends(get_conn),
    _: None = Depends(_verify_bot_secret),
):
    user = await users_repo.get_by_tg_id(conn, body.tg_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    code, expires_at = await login_codes_repo.create(conn, body.tg_id, settings.login_code_ttl_hours)
    logger.info("Сгенерирован код входа для tg_id=%d", body.tg_id)
    return {"code": code, "expires_at": expires_at.isoformat()}


@router.post("/users", response_model=UserResponse)
async def register_user(
    body: UserRegisterRequest,
    conn: asyncpg.Connection = Depends(get_conn),
    _: None = Depends(_verify_bot_secret),
):
    """Регистрация или обновление пользователя."""
    # Если есть реферальный токен, обработаем его
    referral_id = None
    if body.referral_token:
        from app.services.referral import ReferralService
        from app.repositories.referral import ReferralRepo
        referral_repo = ReferralRepo()
        referral_service = ReferralService(referral_repo, users_repo)
        await referral_service.process_redemption(conn, body.tg_id, body.referral_token)
        # После обработки получим referral_id из БД
        referral_link = await referral_repo.get_link_by_token(conn, body.referral_token)
        if referral_link:
            referral_id = referral_link["referrer_tg_id"]

    user = await users_repo.upsert(
        conn,
        tg_id=body.tg_id,
        username=body.username,
        first_name=body.first_name,
        last_name=body.last_name,
        language_code=body.language_code,
        server_id=settings.default_server_id,
        referral_id=referral_id,
    )
    logger.info("Пользователь зарегистрирован/обновлён: tg_id=%d", body.tg_id)
    return UserResponse(
        tg_id=user["tg_id"],
        username=user["username"],
        first_name=user["first_name"],
        trial=user["trial"],
        balance=user["balance"],
        is_blocked=user["is_blocked"],
        is_admin=user["is_admin"],
        created_at=user["created_at"].isoformat() if user["created_at"] else "",
    )


@router.get("/users/{tg_id}", response_model=UserResponse)
async def get_user(
    tg_id: int,
    conn: asyncpg.Connection = Depends(get_conn),
    _: None = Depends(_verify_bot_secret),
):
    """Получить информацию о пользователе."""
    user = await users_repo.get_by_tg_id(conn, tg_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserResponse(
        tg_id=user["tg_id"],
        username=user["username"],
        first_name=user["first_name"],
        trial=user["trial"],
        balance=user["balance"],
        is_blocked=user["is_blocked"],
        is_admin=user["is_admin"],
        created_at=user["created_at"].isoformat() if user["created_at"] else "",
    )


@router.get("/users/{tg_id}/price", response_model=PriceResult)
async def get_user_price(
    tg_id: int,
    tariff_id: int,
    months: int = 1,
    conn: asyncpg.Connection = Depends(get_conn),
    _: None = Depends(_verify_bot_secret),
):
    """Рассчитать цену для пользователя с учётом скидок."""
    from app.services.pricing import PricingService
    from app.repositories.tariffs import TariffsRepo
    from app.repositories.stocks import StocksRepo

    tariffs_repo = TariffsRepo()
    stocks_repo = StocksRepo()
    pricing_service = PricingService(tariffs_repo, stocks_repo)

    price_result = await pricing_service.calculate_price(conn, tg_id, tariff_id, months)
    return PriceResult(
        original_amount=price_result.original_amount,
        final_amount=price_result.final_amount,
        discount_percent=price_result.discount_percent,
        stock_value=price_result.stock_value,
        stock_type=price_result.stock_type,
        has_discount=price_result.has_discount,
        volume_discount_applied=price_result.volume_discount_applied,
    )


@router.post("/keys/trial", response_model=KeyResponse)
async def create_trial_key(
    body: TrialKeyRequest,
    conn: asyncpg.Connection = Depends(get_conn),
    _: None = Depends(_verify_bot_secret),
):
    """Создать пробный (бесплатный) ключ для пользователя."""
    from app.services.keys import create_trial_key

    key_data = await create_trial_key(conn, body.tg_id)
    logger.info("Пробный ключ создан для tg_id=%d", body.tg_id)
    return KeyResponse(
        tg_id=key_data["tg_id"],
        client_id=key_data["client_id"],
        email=key_data["email"],
        key=key_data["key"],
        expiry_time=key_data["expiry_time"],
        total_gb=key_data["total_gb"],
        tariff_id=key_data["tariff_id"],
        inbound_id=key_data["inbound_id"],
        created_at=key_data.get("created_at", 0),
    )


@router.post("/payments", response_model=BotPaymentResponse)
async def create_payment(
    body: BotPaymentRequest,
    conn: asyncpg.Connection = Depends(get_conn),
    _: None = Depends(_verify_bot_secret),
):
    """Создать платёж для создания или продления ключа."""
    from app.services.payments import create_bot_payment

    payment_data = await create_bot_payment(
        conn,
        tg_id=body.tg_id,
        tariff_id=body.tariff_id,
        months=body.months,
        email=body.email,
    )
    logger.info("Платёж создан для бота: tg_id=%d, payment_id=%s", body.tg_id, payment_data["payment_id"])
    return BotPaymentResponse(
        payment_id=payment_data["payment_id"],
        payment_url=payment_data["payment_url"],
        amount=payment_data["amount"],
        original_amount=payment_data["original_amount"],
        discount_percent=payment_data["discount_percent"],
        referral_discount=payment_data["referral_discount"],
    )


@router.get("/referral/{tg_id}/link", response_model=ReferralLinkResponse)
async def get_referral_link(
    tg_id: int,
    conn: asyncpg.Connection = Depends(get_conn),
    _: None = Depends(_verify_bot_secret),
):
    """Получить или создать реферальную ссылку пользователя."""
    from app.services.referral import ReferralService
    from app.repositories.referral import ReferralRepo

    referral_repo = ReferralRepo()
    referral_service = ReferralService(referral_repo, users_repo)

    share_url = await referral_service.get_or_create_link(conn, tg_id)
    link = await referral_repo.get_link_by_tg_id(conn, tg_id)

    logger.info("Реферальная ссылка получена/создана для tg_id=%d", tg_id)
    return ReferralLinkResponse(
        share_url=share_url,
        token=link["token"] if link else "",
    )


@router.get("/referral/{tg_id}/stats", response_model=ReferralStatsResponse)
async def get_referral_stats(
    tg_id: int,
    conn: asyncpg.Connection = Depends(get_conn),
    _: None = Depends(_verify_bot_secret),
):
    """Получить статистику рефералов пользователя."""
    from app.services.referral import ReferralService
    from app.repositories.referral import ReferralRepo

    referral_repo = ReferralRepo()
    referral_service = ReferralService(referral_repo, users_repo)

    share_url = await referral_service.get_or_create_link(conn, tg_id)
    referral_count = await referral_repo.count_referrals(conn, tg_id)
    total_rewards = await referral_repo.sum_referral_rewards(conn, tg_id)

    logger.info("Статистика рефералов получена для tg_id=%d: count=%d, rewards=%f", tg_id, referral_count, total_rewards)
    return ReferralStatsResponse(
        tg_id=tg_id,
        referral_count=referral_count,
        total_rewards=total_rewards,
        share_url=share_url,
    )
