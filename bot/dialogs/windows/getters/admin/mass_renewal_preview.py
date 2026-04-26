"""Геттер для превью массового продления ключей."""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from aiogram_dialog import DialogManager

from dialogs.windows.base import DataGetter
from models import Key
from services.cache.service import CacheService
from services.core.keys.segmentation import KeySegmentationService
from logger import logger


class AdminMassRenewalPreviewGetter(DataGetter):
    """
    Геттер для окна превью массового продления.

    Собирает ключи выбранного сегмента, вычисляет новые даты истечения
    и формирует превью-отчёт.
    """

    def __init__(self, cache: CacheService):
        self.cache = cache

    async def get_data(self, dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
        """
        Получить данные для превью массового продления.

        Возвращает:
        - preview_message: форматированное сообщение с превью
        - keys_to_renew: список ключей для продления
        - days_to_add: количество дней для продления
        - segment: выбранный сегмент
        """
        try:
            segment = dialog_manager.dialog_data.get("selected_segment")
            days = dialog_manager.dialog_data.get("renewal_days")

            if not segment or not days:
                return {
                    "preview_message": "❌ Не выбраны сегмент или количество дней",
                    "keys_to_renew": [],
                    "days_to_add": 0,
                    "segment": "",
                    "total_keys": 0,
                }

            # Получаем все ключи
            all_keys = await self.cache.keys.all()
            if not isinstance(all_keys, list):
                all_keys = [all_keys] if all_keys else []

            # Фильтруем по сегменту
            segmentation = KeySegmentationService()
            keys_to_renew = await self._filter_by_segment(
                segmentation, all_keys, segment
            )

            dialog_manager.dialog_data["keys_to_renew"] = keys_to_renew

            # Формируем превью-сообщение
            preview_message = self._build_preview_message(
                keys_to_renew, days, segment
            )

            return {
                "preview_message": preview_message,
                "keys_to_renew": keys_to_renew,
                "days_to_add": days,
                "segment": segment,
                "total_keys": len(keys_to_renew),
            }

        except Exception as e:
            logger.error(
                "Ошибка при получении данных для превью массового продления",
                error=str(e),
                exc_info=True,
            )
            return {
                "preview_message": f"❌ Ошибка при загрузке превью: {str(e)}",
                "keys_to_renew": [],
                "days_to_add": 0,
                "segment": "",
                "total_keys": 0,
            }

    @staticmethod
    async def _filter_by_segment(
        segmentation: KeySegmentationService,
        keys: List[Key],
        segment: str,
    ) -> List[Key]:
        """Отфильтровать ключи по выбранному сегменту."""
        if segment == "expiring_24h":
            return await segmentation.get_expiring_24h(keys)
        elif segment == "expiring_7d":
            return await segmentation.get_expiring_7d(keys)
        elif segment == "expiring_30d":
            return await segmentation.get_expiring_30d(keys)
        elif segment == "expired":
            return await segmentation.get_expired(keys)
        elif segment == "active":
            return await segmentation.get_active(keys)
        elif segment == "all":
            # Исключаем trial и expired
            now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
            return [k for k in keys if k.expiry_time >= now_ms]
        else:
            return await segmentation.filter_by_name(keys, segment)

    @staticmethod
    def _build_preview_message(
        keys: List[Key],
        days: int,
        segment: str,
        max_preview: int = 15,
    ) -> str:
        """Построить превью-сообщение с деталями продления."""
        segment_names = {
            "expiring_24h": "⏰ Истекают в 24 часа",
            "expiring_7d": "📅 Истекают в 7 дней",
            "expiring_30d": "📆 Истекают в 30 дней",
            "expired": "🔴 Истёкшие ключи",
            "active": "✅ Активные ключи",
            "all": "🔹 Все активные ключи",
        }

        segment_label = segment_names.get(segment, segment)
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

        lines = [
            f"📦 <b>Массовое продление ключей</b>",
            f"",
            f"📂 Сегмент: <b>{segment_label}</b>",
            f"📅 Продление на: <b>{days}</b> дней",
            f"🔑 Ключей для продления: <b>{len(keys)}</b>",
            f"",
        ]

        if not keys:
            lines.append("⚠️ Нет ключей для продления в выбранном сегменте")
            return "\n".join(lines)

        lines.append("<b>Превью изменений:</b>")

        for i, key in enumerate(keys[:max_preview]):
            old_expiry = key.expiry_time
            base_expiry = max(old_expiry, now_ms)
            new_expiry = base_expiry + (days * 24 * 3600 * 1000)

            old_dt = datetime.fromtimestamp(
                old_expiry / 1000, tz=timezone.utc
            ).strftime("%d.%m.%Y")
            new_dt = datetime.fromtimestamp(
                new_expiry / 1000, tz=timezone.utc
            ).strftime("%d.%m.%Y")

            lines.append(f"  <code>{key.email}</code>: {old_dt} → {new_dt}")

        if len(keys) > max_preview:
            lines.append(f"  ... и ещё {len(keys) - max_preview} ключей")

        lines.append("")
        lines.append("Нажмите '✅ Подтвердить' для продления всех ключей")

        return "\n".join(lines)
