from typing import Dict, Any

from aiogram_dialog import DialogManager

from dialogs.windows.base import DataGetter


class MailingConfirmGetter(DataGetter):
    """Получает данные для подтверждения массовой рассылки."""

    async def get_data(self, dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
        """Собирает текст сообщения и список статусов для рассылки."""
        text = dialog_manager.dialog_data.get("text", "Не задано")
        statuses = [
            ("📍 Закрепить сообщение", 1),
            ("❌ Не закреплять", 2),
        ]

        return {
            "text": text,
            "statuses": statuses,
        }
