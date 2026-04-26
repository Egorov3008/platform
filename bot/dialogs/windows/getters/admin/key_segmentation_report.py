"""
Геттер для отображения отчёта по сегментации ключей на админ-панели.
"""

from typing import Dict, Any

from aiogram_dialog import DialogManager
from services.core.keys.admin_report import KeyAdminReport
from logger import logger


class KeySegmentationReportGetter:
    """Геттер для отчёта по сегментированным ключам."""

    def __init__(self):
        self.report = KeyAdminReport()

    async def get_key_report(
        self, dialog_manager: DialogManager, **kwargs
    ) -> Dict[str, Any]:
        """
        Получить отчёт по ключам с сегментацией.

        Args:
            dialog_manager: Менеджер диалогов

        Returns:
            Словарь с данными для вывода в диалог
        """
        try:
            cache = dialog_manager.middleware_data.get("cache")

            if not cache:
                return {
                    "report_message": "❌ Кеш недоступен",
                    "error": True,
                }

            # Получить все ключи из кеша
            all_keys = await cache.keys.all()

            if not isinstance(all_keys, list):
                all_keys = [all_keys] if all_keys else []

            # Получить отчёт
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
        """Получить детали по ключам, истекающим в 24 часа."""
        try:
            cache = dialog_manager.middleware_data.get("cache")

            if not cache:
                return {"details": "❌ Кеш недоступен"}

            all_keys = await cache.keys.all()
            if not isinstance(all_keys, list):
                all_keys = [all_keys] if all_keys else []

            details = await self.report.get_expiring_24h_details(all_keys)

            return {
                "details": details,
                "error": False,
            }

        except Exception as e:
            logger.error(
                "Ошибка при получении детали по истекающим ключам", error=str(e)
            )
            return {
                "details": f"❌ Ошибка: {str(e)}",
                "error": True,
            }

    async def get_expired_details(
        self, dialog_manager: DialogManager, **kwargs
    ) -> Dict[str, Any]:
        """Получить детали по истёкшим ключам."""
        try:
            cache = dialog_manager.middleware_data.get("cache")

            if not cache:
                return {"details": "❌ Кеш недоступен"}

            all_keys = await cache.keys.all()
            if not isinstance(all_keys, list):
                all_keys = [all_keys] if all_keys else []

            details = await self.report.get_expired_details(all_keys)

            return {
                "details": details,
                "error": False,
            }

        except Exception as e:
            logger.error(
                "Ошибка при получении деталей по истёкшим ключам", error=str(e)
            )
            return {
                "details": f"❌ Ошибка: {str(e)}",
                "error": True,
            }
