# from typing import Optional, Dict, Any, List
#
# from config import AVAILABLE_RATES_LIST
# from database.core_models import User, Key, Tariff, Referral
# from aiogram_dialog import DialogManager
# from logger import logger
# from middlewares.cache_middleware import CacheMiddleware
#
#
# async def display_user_info(user_info: dict, tg_id: int) -> Dict[str, Any]:
#     """Отображает информацию о пользователе."""
#     keys: List[Key] = user_info.get("keys")
#     user_data: Optional[User] = user_info.get("user")
#     username = user_data.username if user_data.username else user_data.first_name
#     user_info_message = (
#         f"📊 Информация о пользователе:\n\n"
#         f"🆔 ID пользователя: <b>{tg_id}</b>\n"
#         f"👤 Логин пользователя: <b>{username}</b>\n"
#         f"🔑 Ключи (для редактирования нажмите на ключ):"
#     )
#
#     return {"tg_id": tg_id,
#             "username": username,
#             "keys": keys,
#             "text_msg": user_info_message,
#             }
#
#
# async def getter_welcom_window(dialog_manager: DialogManager, **kwargs):
#     """ геттер для формирования окна приветствия"""
#     tg_id = dialog_manager.event.from_user.id
#     cache: CacheMiddleware = dialog_manager.middleware_data.get("cache")
#     user_info = await cache.get_user(tg_id)
#     tariffs: List[Optional[Tariff]] = await cache.get_tariffs()
#     permitted_rates = [tariff for tariff in tariffs if tariff.id in AVAILABLE_RATES_LIST]
#     discount = 0.0
#     if user_info and user_info.referral_id:
#         referral: Referral = await cache.get_referral_by_referrer(user_info.referral_id)
#         discount = float(referral.discount_percent) if referral else 0.0
#
#     logger.debug("Передаваемые переменные", discount=discount, tariffs=tariffs)
#     return {
#             "discount": discount,
#             "tariffs": permitted_rates or []
#         }
#
#
# async def getter_sending_registration(dialog_manager: DialogManager, **kwargs):
#     """геттер для формирования окна приветствия"""
#
#     username = dialog_manager.dialog_data.get("username")
#     return {"username": username}
