"""Геттеры для окон администрирования ключей (удаление, изменение даты, изменение тарифа)."""

from datetime import datetime
from typing import Dict, Any

from aiogram_dialog import DialogManager

from dialogs.windows.base import DataGetter
from services.cache.key_manager import CacheKeyManager
from services.cache.service import CacheService
from logger import logger


class AdminKeyDeleteGetter(DataGetter):
    """Геттер для окна подтверждения удаления ключа."""

    async def get_data(self, dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
        """Получить данные ключа для отображения при удалении."""
        try:
            cache: CacheService = dialog_manager.middleware_data.get("cache")
            email = dialog_manager.start_data.get("email")

            if not email or not cache:
                return {"email": "", "tg_id": ""}

            key = await cache.keys.get(CacheKeyManager.key(email))
            if not key:
                return {"email": "", "tg_id": ""}

            return {
                "email": key.email,
                "tg_id": key.tg_id,
            }

        except Exception as e:
            logger.error("Ошибка при получении данных ключа для удаления", error=str(e), exc_info=True)
            return {"email": "", "tg_id": ""}


class AdminKeyChangeDateGetter(DataGetter):
    """Геттер для окна выбора даты истечения ключа."""

    async def get_data(self, dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
        """Получить email ключа для отображения заголовка."""
        try:
            cache: CacheService = dialog_manager.middleware_data.get("cache")
            email = dialog_manager.start_data.get("email")

            if not email or not cache:
                return {"email": ""}

            key = await cache.keys.get(CacheKeyManager.key(email))
            if not key:
                return {"email": ""}

            return {
                "email": key.email,
            }

        except Exception as e:
            logger.error("Ошибка при получении данных ключа для изменения даты", error=str(e), exc_info=True)
            return {"email": ""}


class AdminKeyChangeDateConfirmGetter(DataGetter):
    """Геттер для окна подтверждения изменения даты."""

    async def get_data(self, dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
        """Получить email ключа и выбранную дату для подтверждения."""
        try:
            cache: CacheService = dialog_manager.middleware_data.get("cache")
            email = dialog_manager.dialog_data.get("email")
            selected_date = dialog_manager.dialog_data.get("selected_date")

            if not email or not cache or not selected_date:
                return {"email": "", "selected_date_formatted": ""}

            key = await cache.keys.get(CacheKeyManager.key(email))
            if not key:
                return {"email": "", "selected_date_formatted": ""}

            # Форматировать дату для отображения
            date_formatted = selected_date.strftime("%d.%m.%Y")

            return {
                "email": key.email,
                "selected_date_formatted": date_formatted,
            }

        except Exception as e:
            logger.error("Ошибка при получении данных для подтверждения даты", error=str(e), exc_info=True)
            return {"email": "", "selected_date_formatted": ""}


class AdminKeyChangeTariffGetter(DataGetter):
    """Геттер для окна выбора тарифа."""

    async def get_data(self, dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
        """Получить список тарифов и email ключа."""
        try:
            cache: CacheService = dialog_manager.middleware_data.get("cache")
            email = dialog_manager.start_data.get("email")

            if not email or not cache:
                return {"email": "", "tariff_list": []}

            key = await cache.keys.get(CacheKeyManager.key(email))
            if not key:
                return {"email": "", "tariff_list": []}

            # Получить все тарифы из кеша
            tariffs = await cache.tariffs.all()
            if not isinstance(tariffs, list):
                tariffs = [tariffs] if tariffs else []

            # Подготовить список для Select виджета: (id, tariff_object)
            tariff_list = [(str(t.id), t) for t in tariffs]

            return {
                "email": key.email,
                "tariff_list": tariff_list,
            }

        except Exception as e:
            logger.error("Ошибка при получении списка тарифов", error=str(e), exc_info=True)
            return {"email": "", "tariff_list": []}


class AdminKeyChangeTariffConfirmGetter(DataGetter):
    """Геттер для окна подтверждения изменения тарифа."""

    async def get_data(self, dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
        """Получить данные для подтверждения изменения тарифа."""
        try:
            cache: CacheService = dialog_manager.middleware_data.get("cache")
            email = dialog_manager.start_data.get("email")
            selected_tariff_id = dialog_manager.dialog_data.get("selected_tariff_id")

            if not email or not cache or not selected_tariff_id:
                return {"email": "", "tariff_name": "", "total_gb": ""}

            key = await cache.keys.get(CacheKeyManager.key(email))
            tariff = await cache.tariffs.get(CacheKeyManager.tariff(selected_tariff_id))

            if not key or not tariff:
                return {"email": "", "tariff_name": "", "total_gb": ""}

            return {
                "email": key.email,
                "tariff_name": tariff.name_tariff,
                "total_gb": tariff.traffic_limit,
            }

        except Exception as e:
            logger.error("Ошибка при получении данных для подтверждения тарифа", error=str(e), exc_info=True)
            return {"email": "", "tariff_name": "", "total_gb": ""}
