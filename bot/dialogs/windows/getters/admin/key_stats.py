"""Getter для общей статистики ключей с детальной разбивкой по тарифам и 24h окну."""

from datetime import datetime, timezone
from typing import Dict, Any, List, cast
from collections import Counter

from aiogram_dialog import DialogManager

from api.backend_client import BackendAPIClient
from dialogs.windows.base import DataGetter
from models.keys.key import Key
from logger import logger


class KeyStatsGetter(DataGetter):
    """Собирает общую статистику ключей с разбивкой по тарифам и 24h окну."""

    def __init__(self, backend: BackendAPIClient):
        self.backend = backend

    async def _resolve_tariff_name(self, tariff_id: int) -> str:
        """Получает название тарифа по его ID. Возвращает 'ID:{id}' если не найден."""
        try:
            tariff = await self.backend.get_tariff(tariff_id)
            if tariff and tariff.get("name_tariff"):
                return tariff["name_tariff"]
        except Exception:
            pass
        return f"ID:{tariff_id}"

    async def _group_by_tariff_names(self, keys: List[Key]) -> Dict[str, int]:
        """Группирует ключи по названиям тарифов."""
        if not keys:
            return {}

        tariff_ids = set()
        for k in keys:
            if k.tariff_id is not None:
                tariff_ids.add(k.tariff_id)

        tariff_names: Dict[int, str] = {}
        for tid in tariff_ids:
            tariff_names[tid] = await self._resolve_tariff_name(tid)

        counter: Counter = Counter()
        for k in keys:
            if k.tariff_id is not None:
                name = tariff_names.get(k.tariff_id, f"ID:{k.tariff_id}")
                counter[name] += 1
            else:
                counter["Без тарифа"] += 1

        return dict(counter)

    async def _format_tariff_breakdown(self, by_tariff: Dict[str, int]) -> str:
        """Форматирует разбивку по тарифам в строку."""
        if not by_tariff:
            return "     —"
        lines = []
        for name, count in sorted(by_tariff.items(), key=lambda x: -x[1]):
            lines.append(f"     • {name}: {count}")
        return "\n".join(lines)

    def _categorize_keys(self, keys: List[Key]) -> Dict[str, Any]:
        """Разбивает ключи на категории: trial, paid, unused."""
        trial = [k for k in keys if k.tariff_id == 10]
        paid = [k for k in keys if k.tariff_id and 2 <= k.tariff_id <= 9]
        unused = [k for k in keys if k.used_traffic == 0]
        return {
            "trial": trial,
            "paid": paid,
            "unused": unused,
        }

    async def get_data(self, dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
        """Собирает общую статистику всех ключей + детальную 24h разбивку."""
        try:
            raw_keys = await self.backend.admin_list_keys()
            keys_list: List[Key] = [Key.from_backend(k) for k in raw_keys]

            now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
            threshold_24h = now_ms + 24 * 3600 * 1000

            # Фильтруем ключи, истекающие в ближайшие 24 часа
            expiring_24h = [
                key for key in keys_list
                if now_ms < key.expiry_time <= threshold_24h
            ]

            # Категоризация ВСЕХ ключей
            all_cats = self._categorize_keys(keys_list)
            all_trial_by_tariff = await self._group_by_tariff_names(all_cats["trial"])
            all_paid_by_tariff = await self._group_by_tariff_names(all_cats["paid"])
            all_unused_by_tariff = await self._group_by_tariff_names(all_cats["unused"])

            # Категоризация 24h ключей
            exp_cats = self._categorize_keys(expiring_24h)
            exp_trial_by_tariff = await self._group_by_tariff_names(exp_cats["trial"])
            exp_paid_by_tariff = await self._group_by_tariff_names(exp_cats["paid"])
            exp_unused_by_tariff = await self._group_by_tariff_names(exp_cats["unused"])

            # Уведомления только для 24h ключей
            notified_10h_true = [k for k in expiring_24h if k.notified_10h]
            notified_10h_false = [k for k in expiring_24h if not k.notified_10h]
            notified_24h_true = [k for k in expiring_24h if k.notified_24h]
            notified_24h_false = [k for k in expiring_24h if not k.notified_24h]

            stats = {
                # Все ключи
                "all_total": len(keys_list),
                "all_trial": len(all_cats["trial"]),
                "all_paid": len(all_cats["paid"]),
                "all_unused": len(all_cats["unused"]),
                "all_trial_by_tariff": all_trial_by_tariff,
                "all_paid_by_tariff": all_paid_by_tariff,
                "all_unused_by_tariff": all_unused_by_tariff,
                # 24h ключи
                "expiring_24h_total": len(expiring_24h),
                "expiring_24h_trial": len(exp_cats["trial"]),
                "expiring_24h_paid": len(exp_cats["paid"]),
                "expiring_24h_unused": len(exp_cats["unused"]),
                "expiring_24h_trial_by_tariff": exp_trial_by_tariff,
                "expiring_24h_paid_by_tariff": exp_paid_by_tariff,
                "expiring_24h_unused_by_tariff": exp_unused_by_tariff,
                # Уведомления
                "notified_10h_true": len(notified_10h_true),
                "notified_10h_false": len(notified_10h_false),
                "notified_24h_true": len(notified_24h_true),
                "notified_24h_false": len(notified_24h_false),
            }

            dialog_manager.dialog_data["stats"] = stats
            dialog_manager.dialog_data["all_keys"] = keys_list
            dialog_manager.dialog_data["expiring_24h_keys"] = expiring_24h

            # Формируем сообщение
            stats_msg = "🔑 Статистика ключей:\n\n"

            # === Все ключи ===
            stats_msg += f"📊 Все ключи:\n"
            stats_msg += f"   Всего: {stats['all_total']}\n"

            stats_msg += f"   🧪 Trial:\n"
            stats_msg += await self._format_tariff_breakdown(all_trial_by_tariff)
            stats_msg += "\n"

            stats_msg += f"   💰 Платные:\n"
            stats_msg += await self._format_tariff_breakdown(all_paid_by_tariff)
            stats_msg += "\n"

            stats_msg += f"   💤 Неиспользуемые: {stats['all_unused']}\n\n"

            # === 24h ключи ===
            stats_msg += f"⏰ Истекают 24h:\n"
            stats_msg += f"   Всего: {stats['expiring_24h_total']}\n"

            stats_msg += f"   🧪 Trial:\n"
            stats_msg += await self._format_tariff_breakdown(exp_trial_by_tariff)
            stats_msg += "\n"

            stats_msg += f"   💰 Платные:\n"
            stats_msg += await self._format_tariff_breakdown(exp_paid_by_tariff)
            stats_msg += "\n"

            stats_msg += f"   💤 Неиспользуемые:\n"
            stats_msg += await self._format_tariff_breakdown(exp_unused_by_tariff)
            stats_msg += "\n\n"

            # === Уведомления ===
            stats_msg += (
                f"📢 Уведомления 24h:\n"
                f"   ✅ 10h отправлено: {stats['notified_10h_true']} / "
                f"❌ Не отправлено: {stats['notified_10h_false']}\n"
                f"   ✅ 24h отправлено: {stats['notified_24h_true']} / "
                f"❌ Не отправлено: {stats['notified_24h_false']}"
            )

            return {"STATS_MSG": stats_msg, "stats": stats}

        except Exception as e:
            logger.error(
                "Ошибка при получении статистики ключей",
                error=str(e),
                exc_info=True,
            )
            return {"STATS_MSG": f"❌ Ошибка при загрузке статистики: {str(e)}"}
