"""Getter для общей статистики ключей с детальной разбивкой по тарифам и 24h окну."""

from datetime import datetime, timezone
from typing import Dict, Any, List
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

    async def _fetch_tariffs(self) -> List[dict]:
        """Загружает список тарифов из бэкенда."""
        try:
            return await self.backend.admin_list_tariffs() or []
        except Exception as e:
            logger.warning("Не удалось получить список тарифов", error=str(e))
            return []

    @staticmethod
    def _count_keys_by_tariff(keys: List[Key]) -> Counter:
        """
        Сортирует ключи по tariff_id и считает количество на каждый тариф.
        Возвращает Counter: tariff_id -> count.
        Ключи без tariff_id попадают в отдельный ключ None.
        """
        if not keys:
            return Counter()
        # Сортируем ключи по tariff_id (None идут в конец)
        sorted_keys = sorted(keys, key=lambda k: (k.tariff_id is None, k.tariff_id or 0))
        return Counter(k.tariff_id for k in sorted_keys)

    @staticmethod
    def _format_tariff_breakdown(
        tariffs: List[dict], counts: Counter
    ) -> str:
        """
        Формирует строки разбивки по тарифам.

        Алгоритм:
        1. Берём список тарифов (отсортированный по id).
        2. Для каждого тарифа берём name из Tariff.name_tariff
           и count из counts.get(tariff.id, 0).
        3. Тарифы без единого ключа пропускаются.
        4. Ключи с неизвестным tariff_id (нет в tariffs) выводятся как "ID:{id}".
        5. Ключи без tariff_id выводятся как "Без тарифа".
        """
        if not tariffs and not counts:
            return "     —"

        lines: List[str] = []
        known_ids: set = set()
        sorted_tariffs = sorted(
            (t for t in tariffs if isinstance(t, dict) and t.get("id") is not None),
            key=lambda t: t["id"],
        )
        for t in sorted_tariffs:
            tid = t["id"]
            name = t.get("name_tariff") or f"ID:{tid}"
            count = counts.get(tid, 0)
            if count == 0:
                # Тарифы без единого ключа в текущей выборке пропускаем
                continue
            known_ids.add(tid)
            lines.append(f"     • {name}: {count}")

        # Ключи с tariff_id, которого нет в tariffs — отдельно
        unknown_ids = [tid for tid in counts if tid is not None and tid not in known_ids]
        for tid in sorted(unknown_ids):
            lines.append(f"     • ID:{tid}: {counts[tid]}")

        # Ключи без tariff_id
        if None in counts:
            lines.append(f"     • Без тарифа: {counts[None]}")

        return "\n".join(lines) if lines else "     —"

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
            tariffs = await self._fetch_tariffs()

            now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
            threshold_24h = now_ms + 24 * 3600 * 1000

            # Фильтруем ключи, истекающие в ближайшие 24 часа
            expiring_24h = [
                key for key in keys_list
                if now_ms < key.expiry_time <= threshold_24h
            ]

            # Категоризация ВСЕХ ключей: сортируем по tariff_id и считаем по тарифам
            all_cats = self._categorize_keys(keys_list)
            all_trial_counts = self._count_keys_by_tariff(all_cats["trial"])
            all_paid_counts = self._count_keys_by_tariff(all_cats["paid"])
            all_unused_counts = self._count_keys_by_tariff(all_cats["unused"])

            # Категоризация 24h ключей
            exp_cats = self._categorize_keys(expiring_24h)
            exp_trial_counts = self._count_keys_by_tariff(exp_cats["trial"])
            exp_paid_counts = self._count_keys_by_tariff(exp_cats["paid"])
            exp_unused_counts = self._count_keys_by_tariff(exp_cats["unused"])

            # Уведомления только для 24h ключей
            notified_10h_true = [k for k in expiring_24h if k.notified_10h]
            notified_10h_false = [k for k in expiring_24h if not k.notified_10h]
            notified_24h_true = [k for k in expiring_24h if k.notified_24h]
            notified_24h_false = [k for k in expiring_24h if not k.notified_24h]

            # stats-дикты в формате {tariff_name: count} — для обратной совместимости
            def _to_name_dict(counts: Counter) -> Dict[str, int]:
                result: Dict[str, int] = {}
                for t in tariffs:
                    if not isinstance(t, dict) or t.get("id") is None:
                        continue
                    tid = t["id"]
                    if counts.get(tid, 0) > 0:
                        name = t.get("name_tariff") or f"ID:{tid}"
                        result[name] = counts[tid]
                # неизвестные id
                for tid, cnt in counts.items():
                    if tid is not None and not any(
                        isinstance(t, dict) and t.get("id") == tid for t in tariffs
                    ):
                        if cnt > 0:
                            result[f"ID:{tid}"] = cnt
                if None in counts and counts[None] > 0:
                    result["Без тарифа"] = counts[None]
                return result

            stats = {
                "all_total": len(keys_list),
                "all_trial": len(all_cats["trial"]),
                "all_paid": len(all_cats["paid"]),
                "all_unused": len(all_cats["unused"]),
                "all_trial_by_tariff": _to_name_dict(all_trial_counts),
                "all_paid_by_tariff": _to_name_dict(all_paid_counts),
                "all_unused_by_tariff": _to_name_dict(all_unused_counts),
                "expiring_24h_total": len(expiring_24h),
                "expiring_24h_trial": len(exp_cats["trial"]),
                "expiring_24h_paid": len(exp_cats["paid"]),
                "expiring_24h_unused": len(exp_cats["unused"]),
                "expiring_24h_trial_by_tariff": _to_name_dict(exp_trial_counts),
                "expiring_24h_paid_by_tariff": _to_name_dict(exp_paid_counts),
                "expiring_24h_unused_by_tariff": _to_name_dict(exp_unused_counts),
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
            stats_msg += "📊 Все ключи:\n"
            stats_msg += f"   Всего: {stats['all_total']}\n"

            stats_msg += "   🧪 Trial:\n"
            stats_msg += self._format_tariff_breakdown(tariffs, all_trial_counts)
            stats_msg += "\n"

            stats_msg += "   💰 Платные:\n"
            stats_msg += self._format_tariff_breakdown(tariffs, all_paid_counts)
            stats_msg += "\n"

            stats_msg += f"   💤 Неиспользуемые: {stats['all_unused']}\n\n"

            # === 24h ключи ===
            stats_msg += "⏰ Истекают 24h:\n"
            stats_msg += f"   Всего: {stats['expiring_24h_total']}\n"

            stats_msg += "   🧪 Trial:\n"
            stats_msg += self._format_tariff_breakdown(tariffs, exp_trial_counts)
            stats_msg += "\n"

            stats_msg += "   💰 Платные:\n"
            stats_msg += self._format_tariff_breakdown(tariffs, exp_paid_counts)
            stats_msg += "\n"

            stats_msg += "   💤 Неиспользуемые:\n"
            stats_msg += self._format_tariff_breakdown(tariffs, exp_unused_counts)
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
