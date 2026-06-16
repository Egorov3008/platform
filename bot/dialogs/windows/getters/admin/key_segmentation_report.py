"""
Геттер для отображения отчёта по сегментации ключей на админ-панели.
"""

from typing import Dict, Any, List

from aiogram_dialog import DialogManager
from api.backend_client import BackendAPIClient
from services.core.keys.admin_report import KeyAdminReport
from logger import logger


class KeySegmentationReportGetter:
    """Геттер для отчёта по сегментированным ключам через backend API."""

    def __init__(self, backend_client: BackendAPIClient):
        self._backend = backend_client
        self.report = KeyAdminReport()

    async def _get_all_keys(self) -> List:
        raw = await self._backend.admin_list_keys() or []
        # backend returns dicts; KeyAdminReport expects Key objects
        from models import Key
        return [k if isinstance(k, Key) else Key.from_backend(k) for k in raw]

    async def get_key_report(
        self, dialog_manager: DialogManager, **kwargs
    ) -> Dict[str, Any]:
        try:
            all_keys = await self._get_all_keys()
            report_text = await self.report.format_report_text(all_keys)
            stats = await self.report.get_summary_stats(all_keys)
            return {
                "report_message": report_text,
                "error": False,
                "total_keys": stats.get("total", 0),
                "stats": stats,
            }
        except Exception as e:
            logger.error(
                "Ошибка при создании отчёта по ключам", error=str(e), exc_info=True
            )
            return {
                "report_message": f"❌ Ошибка при создании отчёта: {str(e)}",
                "error": True,
            }

    async def get_expiring_24h_details(
        self, dialog_manager: DialogManager, **kwargs
    ) -> Dict[str, Any]:
        try:
            all_keys = await self._get_all_keys()
            details = await self.report.get_expiring_24h_details(all_keys)
            return {"details": details, "error": False}
        except Exception as e:
            logger.error(
                "Ошибка при получении детали по истекающим ключам", error=str(e)
            )
            return {"details": f"❌ Ошибка: {str(e)}", "error": True}

    async def get_expired_details(
        self, dialog_manager: DialogManager, **kwargs
    ) -> Dict[str, Any]:
        try:
            all_keys = await self._get_all_keys()
            details = await self.report.get_expired_details(all_keys)
            return {"details": details, "error": False}
        except Exception as e:
            logger.error(
                "Ошибка при получении деталей по истёкшим ключам", error=str(e)
            )
            return {"details": f"❌ Ошибка: {str(e)}", "error": True}
