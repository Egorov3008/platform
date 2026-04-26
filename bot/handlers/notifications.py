"""
Handlers для обработки callbacks из уведомлений.

Уведомления отправляют inline кнопки с callback_data:
- renew_key|{email} — продление ключа
- activate_stock — активация пробного периода
- connect_vpn — подключение к VPN
- profile — открыть профиль
"""
import punq
from aiogram import F, Router, types
from aiogram_dialog import DialogManager, StartMode

from config import DEFAULT_PRICING_PLAN
from logger import logger
from services.cache.key_manager import CacheKeyManager
from services.cache.service import CacheService
from services.scenarios.create_first_key_scenario import CreateFerstKeyScenario
from states.key import KeysInit
from states.main import MainMenu
from states.payment import PaymentState
from states.referral import ReferralSistem

router = Router()


@router.callback_query(F.data.startswith("renew_key|"))
async def handle_renew_key(query: types.CallbackQuery, dialog_manager: DialogManager):
    """Обработить кнопку 'Продлить ключ' из уведомления"""
    try:
        # Извлечь email из callback_data: "renew_key|user@example.com"
        if not query.data:
            await query.answer("❌ Ошибка при открытии формы", show_alert=True)
            return
        email = query.data.split("|", 1)[1]

        await query.answer("⏳ Открываю форму продления...")

        logger.info(
            "User opened key renewal from notification",
            tg_id=query.from_user.id,
            email=email,
        )

        # Получить CacheService из middleware данных
        cache = dialog_manager.middleware_data.get("cache")
        if not cache:
            logger.error(
                "CacheService not found in middleware_data",
                user_id=query.from_user.id if hasattr(query, "from_user") else None,
                email=email
            )
            await query.answer("❌ Ошибка при открытии формы", show_alert=True)
            return

        key = await cache.keys.get(CacheKeyManager.key(email))
        if not key:
            logger.warning("Key not found in cache", email=email)
            await query.answer("❌ Ключ не найден. Откройте профиль для продления.", show_alert=True)
            return

        default_plan = int(DEFAULT_PRICING_PLAN) if DEFAULT_PRICING_PLAN else 10
        if key.tariff_id == default_plan:
            # Пробный ключ — выбор тарифа
            logger.info(
                "Trial key renewal - navigating to view_tariff",
                tg_id=query.from_user.id,
                email=email,
            )
            await dialog_manager.start(
                PaymentState.view_tariff,
                mode=StartMode.RESET_STACK,
                data={"email": email, "payment_type": "renew_key"},
            )
        else:
            # Платный ключ — сразу к настройке оплаты (выбор месяцев)
            tariff = await cache.tariffs.get(CacheKeyManager.tariff(key.tariff_id))
            amount = float(key.amount or (tariff.amount if tariff else 0))

            logger.info(
                "Paid key renewal - navigating to setting_pay",
                tg_id=query.from_user.id,
                email=email,
                tariff_id=key.tariff_id,
                amount=amount,
            )

            await dialog_manager.start(
                PaymentState.setting_pay,
                mode=StartMode.RESET_STACK,
                data={
                    "email": email,
                    "payment_type": f"renew_key|{email}",
                    "amount": amount,
                    "tariff": tariff,
                },
            )

    except Exception as e:
        logger.error("Error handling renew_key callback", error=str(e), exc_info=True)
        await query.answer("❌ Ошибка при открытии формы", show_alert=True)


@router.callback_query(F.data == "activate_stock")
async def handle_activate_stock(
    query: types.CallbackQuery, dialog_manager: DialogManager
):
    """Обработить кнопку 'Активировать пробный период' из уведомления"""
    try:
        await query.answer("⏳ Открываю пробный период...")

        if not query.from_user:
            logger.error("User not identified in callback")
            await query.answer("❌ Ошибка идентификации", show_alert=True)
            return

        tg_id = query.from_user.id
        logger.info("User activated trial from notification", tg_id=tg_id)


        conteiner: punq.Container | None = dialog_manager.middleware_data.get("container")  # type: ignore[assignment]
        cache: CacheService | None = dialog_manager.middleware_data.get("cache")  # type: ignore[assignment]

        if not conteiner:
            logger.error(
                "Container not found in middleware_data",
                user_id=tg_id,
                handler="activate_stock"
            )
            await query.answer("❌ Ошибка при активации", show_alert=True)
            return

        if not cache:
            logger.error(
                "CacheService not found in middleware_data",
                user_id=tg_id,
                handler="activate_stock"
            )
            await query.answer("❌ Ошибка при активации", show_alert=True)
            return

        create_trial_key = conteiner.resolve(CreateFerstKeyScenario)

        user = await cache.users.get(CacheKeyManager.user(tg_id))  # type: ignore[arg-type]
        if not user:
            logger.error("User not found in cache", tg_id=tg_id)
            await query.answer("❌ Пользователь не найден", show_alert=True)
            return

        create_trial_key.dialog_manager = dialog_manager
        await create_trial_key.start(tg_id, user.server_id)
        

    except Exception as e:
        logger.error(
            "Error handling activate_stock callback", error=str(e), exc_info=True
        )
        await query.answer("❌ Ошибка при активации", show_alert=True)


@router.callback_query(F.data == "connect_vpn")
async def handle_connect_vpn(query: types.CallbackQuery, dialog_manager: DialogManager):
    """Обработить кнопку 'Подключиться' из уведомления напоминания о пробном периоде"""
    try:
        await query.answer("⏳ Показываю инструкцию...")

        logger.info(
            "User opened connection guide from notification", tg_id=query.from_user.id
        )

        # Перейти в диалог выбора устройства и инструкций
        await dialog_manager.start(KeysInit.key, mode=StartMode.RESET_STACK)

    except Exception as e:
        logger.error("Error handling connect_vpn callback", error=str(e), exc_info=True)
        await query.answer("❌ Ошибка при открытии инструкции", show_alert=True)


@router.callback_query(F.data == "open_referral")
async def handle_open_referral(query: types.CallbackQuery, dialog_manager: DialogManager):
    """Обработить кнопку 'Реферальная программа' из уведомления"""
    try:
        await query.answer("⏳ Открываю реферальную программу...")

        logger.info("User opened referral from notification", tg_id=query.from_user.id)

        await dialog_manager.start(ReferralSistem.main, mode=StartMode.RESET_STACK)

    except Exception as e:
        logger.error("Error handling open_referral callback", error=str(e), exc_info=True)
        await query.answer("❌ Ошибка при открытии", show_alert=True)


@router.callback_query(F.data == "profile")
async def handle_open_profile(
    query: types.CallbackQuery, dialog_manager: DialogManager
):
    """Обработить кнопку 'Личный кабинет' / 'Профиль' из уведомления"""
    try:
        await query.answer("⏳ Открываю профиль...")

        logger.info("User opened profile from notification", tg_id=query.from_user.id)

        # Перейти в главное меню профиля пользователя
        await dialog_manager.start(MainMenu.main, mode=StartMode.RESET_STACK)

    except Exception as e:
        logger.error("Error handling profile callback", error=str(e), exc_info=True)
        await query.answer("❌ Ошибка при открытии профиля", show_alert=True)
