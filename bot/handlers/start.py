from typing import Any

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram_dialog import DialogManager, StartMode

from api.backend_client import BackendAPIClient
from config import ADMIN_ID
from aiogram.exceptions import TelegramAPIError
from logger import logger
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
    container = dialog_manager.middleware_data.get("container")
    if not container:
        return
    backend: BackendAPIClient = container.resolve(BackendAPIClient)
    user_info = await backend.get_user(tg_id)

    if not user_info:
        # Незарегистрированный пользователь — авторегистрация
        await auto_register_user(message, dialog_manager)
        return

    if user_info.get("trial", 0) == 0:
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
        if not container:
            await auto_register_user(message, dialog_manager)
            return

        backend: BackendAPIClient = container.resolve(BackendAPIClient)
        gift_scenario = GiftActivationScenario(
            dialog_manager=dialog_manager,
            backend_client=backend,
        )
        await gift_scenario.start()
    elif type_registration == "referral":
        # Реферальная регистрация через backend API
        if not message.from_user:
            return

        tg_id = message.from_user.id
        referrer_tg_id = result_registration.get("referrer_tg_id")
        referral_link_id = result_registration.get("referral_link_id")
        try:
            container = dialog_manager.middleware_data.get("container")
            if not container:
                await auto_register_user(message, dialog_manager)
                return

            backend: BackendAPIClient = container.resolve(BackendAPIClient)

            from_user = message.from_user
            payload = {
                "tg_id": tg_id,
                "username": from_user.username if from_user else None,
                "first_name": from_user.first_name if from_user else None,
                "last_name": from_user.last_name if from_user else None,
                "language_code": from_user.language_code if from_user else None,
                "server_id": 2,
                "referral_id": referrer_tg_id,
                "referral_link_id": referral_link_id,
            }

            new_user = await backend.admin_register_user(payload)
            if not new_user or not new_user.get("tg_id"):
                raise RuntimeError("Backend referral registration failed")

            logger.info(
                "Пользователь зарегистрирован по реферальной ссылке через backend",
                tg_id=tg_id,
                referrer_tg_id=referrer_tg_id,
            )

            # Уведомляем админов о реферальной регистрации
            new_name = from_user.full_name if from_user and from_user.full_name else ""
            new_username = f"@{from_user.username}" if from_user and from_user.username else "нет"

            ref_username = "нет"
            if referrer_tg_id and isinstance(referrer_tg_id, int):
                referrer = await backend.get_user(referrer_tg_id)
                if referrer:
                    ref_username = f"@{referrer.get('username')}" if referrer.get("username") else "нет"

            # Подсчёт рефералов у пригласившего
            all_users = await backend.admin_list_users()
            referral_count = sum(
                1 for u in all_users
                if u.get("referral_id") == referrer_tg_id
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
        if result_registration.get("trial", 0) == 0:
            await dialog_manager.start(MainMenu.welcome, mode=StartMode.RESET_STACK)
        else:
            await dialog_manager.start(MainMenu.main, mode=StartMode.RESET_STACK)
    else:
        raise AttributeError("Неизвестный тип регистрации")


# except Exception as e:
#     logger.error(f"Ошибка при отображении окна", type=type_registration, error_type=type(e).__name__,
#                  error_message=str(e), exc_info=True)
