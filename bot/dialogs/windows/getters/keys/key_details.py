from typing import Dict, Any

from aiogram_dialog import DialogManager

from api.backend_client import BackendAPIClient
from dialogs.windows.base import DataGetter


class KeyDetailsGetter(DataGetter):
    """Геттер для окна детального просмотра ключа."""

    def __init__(self, backend_client: BackendAPIClient):
        self._backend = backend_client

    async def get_data(self, dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
        email = dialog_manager.dialog_data.get("email")
        if not email:
            return {"error": True, "error_message": "❌ Email не найден", "keys": "", "not_error": False}

        data = await self._backend.get_key_details(email)
        if not data:
            return {"error": True, "error_message": "❌ Ключ не найден", "keys": "", "not_error": False}

        used_bytes = data.get("used_traffic") or 0
        used_traffic = round(used_bytes / (1024 ** 3), 2)

        days_left = data.get("days_left", 0)
        hours_left = data.get("hours_left", 0)
        is_active = data.get("is_active", False)

        if not is_active:
            status_emoji, time_left_message = "🔴", "Осталось часов: 0"
        elif days_left > 0:
            status_emoji, time_left_message = "🟢", f"Осталось дней: {days_left}"
        else:
            status_emoji, time_left_message = "🟡", f"Осталось часов: {hours_left}"

        tariff_id = data.get("tariff_id")

        return {
            "error": False,
            "not_error": True,
            "keys": data.get("key", ""),
            "tariff_name": data.get("name_tariff") or "Не указан",
            "used_traffic": used_traffic,
            "expiry_date": data.get("expiry_date", ""),
            "status_emoji": status_emoji,
            "status_text": data.get("status_text", ""),
            "time_left_message": time_left_message,
            "is_trial": data.get("is_trial", False),
            "not_trial_tariff": tariff_id != 10 if tariff_id is not None else True,
            "is_active": is_active,
            "days_left": days_left,
            "hours_left": hours_left,
        }
