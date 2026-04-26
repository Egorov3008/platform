"""DataGetter для админ-диалога генерации ключа."""

from typing import Dict, Any

from aiogram_dialog import DialogManager

from client import XUISession
from dialogs.windows.base import DataGetter
from models import Inbound, Tariff
from services.cache.key_manager import CacheKeyManager
from services.cache.service import CacheService
from logger import logger


class AdminGenKeyGetter(DataGetter):
    """Получает данные для диалога генерации ключа администратором."""

    def __init__(self, cache_service: CacheService):
        self.cache = cache_service

    async def _load_inbounds(self, dialog_manager: DialogManager) -> list:
        """Загружает inbounds из кеша, при отсутствии — обновляет из 3x-ui панели."""
        all_inbounds = await self.cache.inbounds.all()
        if not isinstance(all_inbounds, list):
            all_inbounds = [all_inbounds] if all_inbounds else []

        if all_inbounds:
            return all_inbounds

        # Кеш пуст — загружаем из панели
        logger.info("Inbounds отсутствуют в кеше, загрузка из 3x-ui панели")
        container = dialog_manager.middleware_data.get("container")
        if not container:
            return []

        xui_session: XUISession = container.resolve(XUISession)
        panel_inbounds = await xui_session.get_inbounds()
        if not panel_inbounds:
            logger.warning(
                "Не удалось получить inbounds из панели",
                server_id=getattr(xui_session, "server_id", "unknown")
            )
            return []

        server_id = xui_session.server_id
        for panel_inbound in panel_inbounds:
            inbound_id = panel_inbound.id
            cache_key = CacheKeyManager.inbound(server_id, inbound_id)
            inbound_model = Inbound(
                server_id=server_id,
                inbound_id=inbound_id,
                name_inbound=panel_inbound.remark or f"Inbound {inbound_id}",
            )
            await self.cache.inbounds.set(cache_key, inbound_model)

        all_inbounds = await self.cache.inbounds.all()
        if not isinstance(all_inbounds, list):
            all_inbounds = [all_inbounds] if all_inbounds else []
        return all_inbounds

    async def _load_tariffs(self) -> list:
        """Загружает тарифы из кеша."""
        tariffs = await self.cache.tariffs.all()
        if not isinstance(tariffs, list):
            tariffs = [tariffs] if tariffs else []
        return [t for t in tariffs if isinstance(t, Tariff)]

    async def get_data(self, dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
        """Собирает данные для всех состояний диалога генерации ключа."""
        try:
            tg_id = dialog_manager.dialog_data.get("tg_id")
            user_exists = dialog_manager.dialog_data.get("user_exists", False)
            result = dialog_manager.dialog_data.get("result")

            # Загружаем inbounds и тарифы
            all_inbounds = await self._load_inbounds(dialog_manager)
            all_tariffs = await self._load_tariffs()

            # Статус пользователя
            user_status = "✅ Существует" if user_exists else "🆕 Будет создан"

            # Имя выбранного inbound
            inbound_name = "не выбрано"
            widget_data = dialog_manager.current_context().widget_data
            selected_inbound_id = widget_data.get("gen_inbound_radio")
            if selected_inbound_id:
                for inbound in all_inbounds:
                    if isinstance(inbound, Inbound) and str(inbound.inbound_id) == str(
                        selected_inbound_id
                    ):
                        inbound_name = inbound.name_inbound
                        break

            # Имя выбранного тарифа
            tariff_name = "не выбран"
            selected_tariff_id = widget_data.get("gen_tariff_radio")
            if selected_tariff_id:
                for tariff in all_tariffs:
                    if str(tariff.id) == str(selected_tariff_id):
                        tariff_name = tariff.name_tariff
                        break

            # Данные результата
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
