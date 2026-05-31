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
        # If any gift is not yet redeemed (no redeemed_at / recipient_tg_id)
        for gift in gifts:
            if not gift.get("redeemed_at") and not gift.get("recipient_tg_id"):
                return True
        return False
