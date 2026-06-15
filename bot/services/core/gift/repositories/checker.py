from typing import Optional

from api.backend_client import BackendAPIClient


class CheckerGiftLink:
    """Проверяет использование подарка через Backend API."""

    def __init__(self, backend: BackendAPIClient):
        self._backend = backend

    async def check(self, user_id: int) -> bool:
        gifts = await self._backend.admin_list_gifts(sender_tg_id=user_id)
        if not gifts:
            return False
        # If any gift is not yet redeemed (no recipient/used_by_tg_id)
        for gift in gifts:
            # Backend returns dicts with snake_case fields; DTO uses used_by_tg_id.
            if isinstance(gift, dict):
                redeemed = gift.get("redeemed_at") or gift.get("used_at")
                recipient = gift.get("recipient_tg_id") or gift.get("used_by_tg_id")
            else:
                redeemed = getattr(gift, "expires_at", None) is None and not getattr(gift, "is_used", False)
                recipient = getattr(gift, "used_by_tg_id", None)
            if not redeemed and not recipient:
                return True
        return False
