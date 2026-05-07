import random
from typing import Any

import asyncpg
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram_dialog import DialogManager, StartMode

from config import LIST_AVAILABLE_CONNECTIONS, ADMIN_ID
from aiogram.exceptions import TelegramAPIError
from logger import logger
from models.referrals.referral_redemption import ReferralRedemption
from services.cache.key_manager import CacheKeyManager
from services.cache.service import CacheService
from services.core.data.service import ServiceDataModel
from services.core.user.utils.saver import SeverUser
from services.core.user.utils.auto_register import auto_register_user
from services.scenarios.gift_scenario import GiftActivationScenario
from states.admin import AdminSearchManagementSG
from states.main import MainMenu

router = Router()


@router.message(Command("profile"))
async def send_massage_user_start(
    message: Message, dialog_manager: DialogManager
) -> Any:
    """Отправляет сообщение после подтверждения регистрации юзеру"""

    if not message.from_user:
        return

    tg_id = message.from_user.id
    cache = dialog_manager.middleware_data.get("cache")
    if not isinstance(cache, CacheService):
        return
    user_info = await cache.users.get(CacheKeyManager.user(tg_id))

    if not user_info:
        # Незарегистрированный пользователь — авторегистрация
        await auto_register_user(message, dialog_manager)
        return

    if user_info.trial == 0:
        await dialog_manager.start(MainMenu.welcome, mode=StartMode.RESET_STACK)
    else:
        await dialog_manager.start(MainMenu.main, mode=StartMode.RESET_STACK)


@router.message(Command("start"))
async def send_massage_registration(
    message: Message, dialog_manager: DialogManager
) -> Any:
    """Перенаправляет пользователя в зависимости от типа"""
    type_registration = None

    # Если это запрос поиска пользователя от администратора — открываем профиль напрямую
    admin_search_tg_id: int | None = dialog_manager.middleware_data.get(
        "admin_search_tg_id"
    )
    if admin_search_tg_id is not None:
        await dialog_manager.start(
            AdminSearchManagementSG.profile_user,
            mode=StartMode.RESET_STACK,
            data={"tg_id": admin_search_tg_id},
        )
        return

    result_registration = dialog_manager.middleware_data.get(
        "registration_result"
    )
    logger.debug(
        "Полученные параметры", type=type_registration, result=result_registration
    )
    if not isinstance(result_registration, dict):
        await auto_register_user(message, dialog_manager)
        return
    type_registration = result_registration.get("type")
    if type_registration == "unknown_user":
        await auto_register_user(message, dialog_manager)
    elif result_registration.get("type") == "gift":
        container = dialog_manager.middleware_data.get("container")
        cache = dialog_manager.middleware_data.get("cache")

        if not container or not cache:
            await auto_register_user(message, dialog_manager)
            return

        service_model: ServiceDataModel = container.resolve(ServiceDataModel)
        saver: SeverUser = container.resolve(SeverUser)

        gift_scenario = GiftActivationScenario(
            dialog_manager=dialog_manager,
            service_model=service_model,
            saver=saver,
            cache=cache,
        )
        await gift_scenario.start()
    elif type_registration == "referral":
        # Реферальная регистрация: авто-создаём пользователя и перенаправляем в главное меню
        if not message.from_user:
            return

        tg_id = message.from_user.id
        referrer_tg_id = result_registration.get("referrer_tg_id")
        referral_link_id = result_registration.get("referral_link_id")
        try:
            container = dialog_manager.middleware_data.get("container")
            cache = dialog_manager.middleware_data.get("cache")

            if not container or not isinstance(cache, CacheService):
                await auto_register_user(message, dialog_manager)
                return

            pool: asyncpg.Pool = container.resolve(asyncpg.Pool)
            referral_saver: SeverUser = container.resolve(SeverUser)
            referral_service_model: ServiceDataModel = container.resolve(ServiceDataModel)

            # Выбираем случайный inbound из доступных подключений
            inbound_id = random.choice(LIST_AVAILABLE_CONNECTIONS)

            # Создаём пользователя в БД (server_id всегда 2)
            new_user = await referral_saver.register_user(
                pool, tg_id=tg_id, server_id=2, referral_id=referrer_tg_id
            )

            # Кешируем нового пользователя
            await cache.users.set(CacheKeyManager.user(tg_id), new_user)

            # Сохраняем выбранный inbound_id во временный кеш для CreateFirstKeyScenario
            await cache.users.set(
                CacheKeyManager.temporary_inbound(tg_id), str(inbound_id)
            )

            # Записываем реферальную привязку в БД
            if referral_link_id:
                redemption = ReferralRedemption(
                    referral_link_id=referral_link_id,
                    referred_tg_id=tg_id,
                )
                await referral_service_model.data_service.referral_redemptions.create(
                    pool, **redemption.to_dict()
                )
                logger.info(
                    "Реферальная привязка создана",
                    referrer_tg_id=referrer_tg_id,
                    referred_tg_id=tg_id,
                )

            # Уведомляем админов о реферальной регистрации
            from_user = message.from_user
            new_name = from_user.full_name if from_user and from_user.full_name else ""
            new_username = f"@{from_user.username}" if from_user and from_user.username else "нет"

            ref_username = "нет"
            if referrer_tg_id and isinstance(referrer_tg_id, int):
                referrer = await cache.users.get(CacheKeyManager.user(referrer_tg_id))
                if referrer:
                    ref_username = f"@{referrer.username}" if referrer.username else "нет"

            # Подсчёт рефералов у пригласившего
            all_users = await cache.users.all()
            referral_count = sum(
                1 for u in all_users
                if getattr(u, "referral_id", None) == referrer_tg_id
            )

            admin_text = (
                "👥 <b>Реферальная регистрация</b>\n\n"
                "👤 <b>Новый пользователь:</b>\n"
                f"  • ID: <code>{tg_id}</code>\n"
                f"  • Имя: {new_name}\n"
                f"  • Username: {new_username}\n\n"
                "🔗 <b>Пригласил:</b>\n"
                f"  • ID: <code>{referrer_tg_id}</code>\n"
                f"  • Username: {ref_username}\n\n"
                f"📊 Всего рефералов у пригласившего: <b>{referral_count}</b>"
            )
            for admin_id in ADMIN_ID:
                try:
                    if message.bot:
                        await message.bot.send_message(
                            chat_id=admin_id,
                            text=admin_text,
                            parse_mode="HTML",
                        )
                except TelegramAPIError:
                    pass

            await dialog_manager.start(MainMenu.welcome, mode=StartMode.RESET_STACK)
        except Exception as e:
            logger.error(
                "Ошибка при авто-регистрации реферального пользователя",
                tg_id=tg_id,
                error_type=type(e).__name__,
                error_message=str(e),
                exc_info=True,
            )
            # Fallback: авторегистрация при ошибке
            await auto_register_user(message, dialog_manager)
    elif type_registration == "registered_user":
        await dialog_manager.start(MainMenu.main, mode=StartMode.RESET_STACK)
    else:
        raise AttributeError("Неизвестный тип регистрации")


# except Exception as e:
#     logger.error(f"Ошибка при отображении окна", type=type_registration, error_type=type(e).__name__,
#                  error_message=str(e), exc_info=True)
