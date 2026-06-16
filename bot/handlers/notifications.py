"""
Handlers для обработки callbacks из уведомлений.

Уведомления отправляют inline кнопки с callback_data:
- renew_key|{email} — продление ключа
- activate_stock — активация пробного периода
- connect_vpn — подключение к VPN
- profile — открыть профиль
"""
from aiogram import F, Router, types
from aiogram_dialog import DialogManager, StartMode

from api.backend_client import BackendAPIClient
from config import DEFAULT_PRICING_PLAN
from logger import logger
from models import Tariff
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

        container = dialog_manager.middleware_data.get("container")
        if not container:
            logger.error(
                "Container not found in middleware_data",
                user_id=query.from_user.id if hasattr(query, "from_user") else None,
                email=email
            )
            await query.answer("❌ Ошибка при открытии формы", show_alert=True)
            return

        backend: BackendAPIClient = container.resolve(BackendAPIClient)
        key = await backend.get_key(email)
        if not key:
            logger.warning("Key not found in backend", email=email)
            await query.answer("❌ Ключ не найден. Откройте профиль для продления.", show_alert=True)
            return

        default_plan = int(DEFAULT_PRICING_PLAN) if DEFAULT_PRICING_PLAN else 10
        if key.tariff_id == default_plan:
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
            tariff_dict = await backend.get_tariff(key.tariff_id)
            if not tariff_dict:
                await query.answer("❌ Тариф не найден", show_alert=True)
                return

            tariff = Tariff.from_dict(tariff_dict)
            # KeyDTO не содержит amount — стоимость продления всегда берётся из тарифа
            amount = float(tariff.amount)

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
                    "number_of_months": 1,
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

        container = dialog_manager.middleware_data.get("container")
        if not container:
            logger.error(
                "Container not found in middleware_data",
                user_id=tg_id,
                handler="activate_stock"
            )
            await query.answer("❌ Ошибка при активации", show_alert=True)
            return

        backend: BackendAPIClient = container.resolve(BackendAPIClient)
        user = await backend.get_user(tg_id)
        if not user:
            logger.error("User not found in backend", tg_id=tg_id)
            await query.answer("❌ Пользователь не найден", show_alert=True)
            return

        create_trial_key = container.resolve(CreateFerstKeyScenario)
        create_trial_key.dialog_manager = dialog_manager
        await create_trial_key.start(tg_id, user.get("server_id", 2))

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
