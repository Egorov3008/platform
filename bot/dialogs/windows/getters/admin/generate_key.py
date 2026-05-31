"""DataGetter для админ-диалога генерации ключа."""

from typing import Dict, Any, List

from aiogram_dialog import DialogManager

from api.backend_client import BackendAPIClient
from dialogs.windows.base import DataGetter
from models import Inbound, Tariff
from logger import logger


class AdminGenKeyGetter(DataGetter):
    """Получает данные для диалога генерации ключа администратором через backend API."""

    def __init__(self, backend_client: BackendAPIClient):
        self._backend = backend_client

    async def _load_inbounds(self) -> List[Inbound]:
        """Загружает inbounds из backend API."""
        raw = await self._backend.admin_list_inbounds()
        result = []
        for item in raw:
            if isinstance(item, dict):
                result.append(Inbound(**item))
            elif isinstance(item, Inbound):
                result.append(item)
        return result

    async def _load_tariffs(self) -> List[Tariff]:
        """Загружает тарифы из backend API."""
        raw = await self._backend.admin_list_tariffs()
        result = []
        for item in raw:
            if isinstance(item, dict):
                result.append(Tariff(**item))
            elif isinstance(item, Tariff):
                result.append(item)
        return result

    async def get_data(self, dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
        """Собирает данные для всех состояний диалога генерации ключа."""
        try:
            tg_id = dialog_manager.dialog_data.get("tg_id")
            user_exists = dialog_manager.dialog_data.get("user_exists", False)
            result = dialog_manager.dialog_data.get("result")

            all_inbounds = await self._load_inbounds()
            all_tariffs = await self._load_tariffs()

            user_status = "✅ Существует" if user_exists else "🆕 Будет создан"

            inbound_name = "не выбрано"
            widget_data = dialog_manager.current_context().widget_data
            selected_inbound_id = widget_data.get("gen_inbound_radio")
            if selected_inbound_id:
                for inbound in all_inbounds:
                    if str(inbound.inbound_id) == str(selected_inbound_id):
                        inbound_name = inbound.name_inbound
                        break

            tariff_name = "не выбран"
            selected_tariff_id = widget_data.get("gen_tariff_radio")
            if selected_tariff_id:
                for tariff in all_tariffs:
                    if str(tariff.id) == str(selected_tariff_id):
                        tariff_name = tariff.name_tariff
                        break

            email = ""
            link_to_connect = ""
            days = 0
            if result:
                email = result.get("email", "")
                link_to_connect = result.get("link_to_connect", "")
                days = result.get("days", 0)

            return {
                "tg_id": tg_id or "",
                "user_status": user_status,
                "inbounds": all_inbounds,
                "tariffs": all_tariffs,
                "inbound_name": inbound_name,
                "tariff_name": tariff_name,
                "email": email,
                "link_to_connect": link_to_connect,
                "days": days,
            }

        except Exception as e:
            logger.error(
                "Ошибка при получении данных для диалога генерации ключа",
                error=str(e),
                exc_info=True,
            )
            return {
                "tg_id": "",
                "user_status": "",
                "inbounds": [],
                "tariffs": [],
                "inbound_name": "",
                "tariff_name": "",
                "email": "",
                "link_to_connect": "",
                "days": 0,
            }
