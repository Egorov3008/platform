from typing import Optional

from aiogram_dialog import DialogManager

from dialogs.windows.base import DataGetter
from models import ReferralLink
from services.core.data.service import ServiceDataModel
from services.core.referral.link_generator import ReferralLinkGenerator


class ReferralMainGetter(DataGetter):
    """Геттер для окна реферальной программы."""

    def __init__(
        self,
        model_data: ServiceDataModel,
        link_generator: ReferralLinkGenerator,
    ):
        self._referral_data = model_data.referral_links
        self._link_generator = link_generator
        self._data_service = model_data.data_service
        self._users = model_data.users

    async def get_data(self, dialog_manager: DialogManager, **kwargs) -> dict:
        tg_id = dialog_manager.event.from_user.id
        session = dialog_manager.middleware_data.get("session")

        # Ищем существующую ссылку пользователя
        link: Optional[ReferralLink] = await self._referral_data.get_by(
            referrer_tg_id=tg_id
        )

        if link and session:
            share_url = self._link_generator.get_share_url(link.token)

            # Считаем количество рефералов и наград
            all_redemptions = await self._data_service.referral_redemptions.get_all(
                session
            )
            referral_count = sum(
                1 for r in all_redemptions if r.referral_link_id == link.id
            ) if all_redemptions else 0

            all_rewards = await self._data_service.referral_rewards.get_all(
                session
            )
            user_rewards = [
                r for r in all_rewards if r.referrer_tg_id == tg_id
            ] if all_rewards else []
            rewards_count = len(user_rewards)
            rewards_total = sum(
                float(r.reward_value) for r in user_rewards
            )

            user = await self._users.get_data(tg_id)
            available_balance = user.balance if user else 0.0

            return {
                "has_link": True,
                "no_link": False,
                "share_url": share_url,
                "referral_count": referral_count,
                "rewards_count": rewards_count,
                "rewards_total": rewards_total,
                "available_balance": available_balance,
            }

        return {
            "has_link": False,
            "no_link": True,
            "share_url": "",
            "referral_count": 0,
            "rewards_count": 0,
            "rewards_total": 0.0,
            "available_balance": 0.0,
        }
