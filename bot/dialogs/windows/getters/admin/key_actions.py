"""Геттеры для окон администрирования ключей (удаление, изменение даты, изменение тарифа)."""

from typing import Dict, Any, List, Optional

from aiogram_dialog import DialogManager

from api.backend_client import BackendAPIClient
from dialogs.windows.base import DataGetter
from models import Tariff
from logger import logger


class AdminKeyDeleteGetter(DataGetter):
    """Геттер для окна подтверждения удаления ключа."""

    def __init__(self, backend_client: BackendAPIClient):
        self._backend = backend_client

    async def get_data(self, dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
        try:
            email = dialog_manager.start_data.get("email")
            if not email:
                return {"email": "", "tg_id": ""}
            key = await self._backend.get_key_details(email)
            if not key:
                return {"email": "", "tg_id": ""}
            return {"email": key.get("email", ""), "tg_id": key.get("tg_id", "")}
        except Exception as e:
            logger.error("Ошибка при получении данных ключа для удаления", error=str(e), exc_info=True)
            return {"email": "", "tg_id": ""}


class AdminKeyChangeDateGetter(DataGetter):
    """Геттер для окна выбора даты истечения ключа."""

    def __init__(self, backend_client: BackendAPIClient):
        self._backend = backend_client

    async def get_data(self, dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
        try:
            email = dialog_manager.start_data.get("email")
            if not email:
                return {"email": ""}
            key = await self._backend.get_key_details(email)
            if not key:
                return {"email": ""}
            return {"email": key.get("email", "")}
        except Exception as e:
            logger.error("Ошибка при получении данных ключа для изменения даты", error=str(e), exc_info=True)
            return {"email": ""}


class AdminKeyChangeDateConfirmGetter(DataGetter):
    """Геттер для окна подтверждения изменения даты."""

    def __init__(self, backend_client: BackendAPIClient):
        self._backend = backend_client

    async def get_data(self, dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
        try:
            email = dialog_manager.dialog_data.get("email")
            selected_date = dialog_manager.dialog_data.get("selected_date")
            if not email or not selected_date:
                return {"email": "", "selected_date_formatted": ""}
            key = await self._backend.get_key_details(email)
            if not key:
                return {"email": "", "selected_date_formatted": ""}
            date_formatted = selected_date.strftime("%d.%m.%Y")
            return {"email": key.get("email", ""), "selected_date_formatted": date_formatted}
        except Exception as e:
            logger.error("Ошибка при получении данных для подтверждения даты", error=str(e), exc_info=True)
            return {"email": "", "selected_date_formatted": ""}


class AdminKeyChangeTariffGetter(DataGetter):
    """Геттер для окна выбора тарифа."""

    def __init__(self, backend_client: BackendAPIClient):
        self._backend = backend_client

    async def get_data(self, dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
        try:
            email = dialog_manager.start_data.get("email")
            if not email:
                return {"email": "", "tariff_list": []}
            key = await self._backend.get_key_details(email)
            if not key:
                return {"email": "", "tariff_list": []}
            tariffs = await self._backend.admin_list_tariffs()
            tariff_list = []
            for t in tariffs:
                if isinstance(t, Tariff):
                    tariff_obj = t
                elif isinstance(t, dict):
                    tariff_obj = Tariff.from_dict(t)
                else:
                    continue
                tariff_list.append((str(tariff_obj.id), tariff_obj))
            return {"email": key.get("email", ""), "tariff_list": tariff_list}
        except Exception as e:
            logger.error("Ошибка при получении списка тарифов", error=str(e), exc_info=True)
            return {"email": "", "tariff_list": []}


class AdminKeyChangeTariffConfirmGetter(DataGetter):
    """Геттер для окна подтверждения изменения тарифа."""

    def __init__(self, backend_client: BackendAPIClient):
        self._backend = backend_client

    async def get_data(self, dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
        try:
            email = dialog_manager.start_data.get("email")
            selected_tariff_id = dialog_manager.dialog_data.get("selected_tariff_id")
            if not email or not selected_tariff_id:
                return {"email": "", "tariff_name": ""}
            key = await self._backend.get_key_details(email)
            tariff = await self._backend.get_tariff(int(selected_tariff_id))
            if not key or not tariff:
                return {"email": "", "tariff_name": ""}
            return {
                "email": key.get("email", ""),
                "tariff_name": tariff.get("name_tariff", ""),
            }
        except Exception as e:
            logger.error("Ошибка при получении данных для подтверждения тарифа", error=str(e), exc_info=True)
            return {"email": "", "tariff_name": ""}
