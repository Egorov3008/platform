from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Tuple

from aiogram_dialog import DialogManager

from api.backend_client import BackendAPIClient
from dialogs.windows.base import DataGetter
from models.keys.key import Key
from logger import logger


class AdminStatsGetter(DataGetter):
    """Получает статистику пользователей: регистрации, отток, заблокированные."""

    def __init__(self, backend: BackendAPIClient):
        self.backend = backend

    # ------------------------------------------------------------------
    # Вспомогательные методы
    # ------------------------------------------------------------------

    @staticmethod
    def _get_week_boundaries(now: datetime) -> Tuple[datetime, datetime]:
        """Возвращает (start, end) текущей недели: понедельник 00:00 — воскресенье 23:59 UTC."""
        days_since_monday = now.weekday()
        monday = now.replace(
            hour=0, minute=0, second=0, microsecond=0
        ) - timedelta(days=days_since_monday)
        sunday = monday.replace(hour=23, minute=59, second=59) + timedelta(days=6)
        return monday, sunday

    @staticmethod
    def _parse_created_at(u: dict) -> datetime:
        """Парсит created_at из backend response."""
        created = u.get("created_at")
        if isinstance(created, datetime):
            return created
        if isinstance(created, str):
            # Обрезаем микросекунды если они есть (Python < 3.11)
            if "." in created:
                created = created.split(".")[0]
            return datetime.fromisoformat(created.replace("Z", "+00:00"))
        return datetime.min.replace(tzinfo=timezone.utc)

    def _count_registrations(
        self, users: List[dict], start: datetime, end: datetime
    ) -> int:
        """Считает пользователей, зарегистрированных в [start, end]."""
        count = 0
        for u in users:
            created = self._parse_created_at(u)
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            if start <= created <= end:
                count += 1
        return count

    async def _count_churn(
        self, users: List[dict], keys: List[Key], start: datetime, end: datetime
    ) -> int:
        """
        Считает пользователей в оттоке.
        Отток — пользователь, у которого ВСЕ ключи истекли в периоде
        и при этом нет ни одного активного ключа.
        """
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        start_ms = int(start.timestamp() * 1000)
        end_ms = int(end.timestamp() * 1000)

        keys_by_user: Dict[int, List[Key]] = {}
        for k in keys:
            keys_by_user.setdefault(k.tg_id, []).append(k)

        churned = 0
        for u in users:
            tg_id = u.get("tg_id")
            user_keys = keys_by_user.get(tg_id, [])
            if not user_keys:
                continue

            all_expired = all(k.expiry_time < now_ms for k in user_keys)
            if not all_expired:
                continue

            all_in_period = all(start_ms <= k.expiry_time <= end_ms for k in user_keys)
            if all_in_period:
                churned += 1

        return churned

    @staticmethod
    def _count_blocked(users: List[dict]) -> int:
        """Считает пользователей с is_blocked == True."""
        return sum(1 for u in users if u.get("is_blocked"))

    # ------------------------------------------------------------------
    # Основной метод
    # ------------------------------------------------------------------

    async def get_data(self, dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
        """Собирает статистику пользователей."""
        try:
            users_raw = await self.backend.admin_list_users()
            keys_raw = await self.backend.admin_list_keys()

            users_list: List[dict] = users_raw if isinstance(users_raw, list) else []
            keys_list: List[Key] = [Key.from_backend(k) for k in keys_raw]

            total_users = len(users_list)

            now = datetime.now(timezone.utc)
            monday, sunday = self._get_week_boundaries(now)
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            year_start = now.replace(
                month=1, day=1, hour=0, minute=0, second=0, microsecond=0
            )

            # Регистрации
            reg_week = self._count_registrations(users_list, monday, sunday)
            reg_month = self._count_registrations(users_list, month_start, now)
            reg_year = self._count_registrations(users_list, year_start, now)

            # Отток
            churn_week = await self._count_churn(
                users_list, keys_list, monday, sunday
            )
            churn_month = await self._count_churn(
                users_list, keys_list, month_start, now
            )
            churn_year = await self._count_churn(
                users_list, keys_list, year_start, now
            )

            # Заблокированные
            blocked = self._count_blocked(users_list)

            # Сохраняем ключи для других обработчиков
            dialog_manager.dialog_data["all_keys"] = keys_list

            stats_msg = (
                f"👥 <b>Пользователи</b>\n"
                f"   🌐 Всего: {total_users}\n"
                f"   📈 Новые за неделю: {reg_week}\n"
                f"   📈 Новые за месяц: {reg_month}\n"
                f"   📈 Новые за год: {reg_year}\n"
                f"   📉 Отток за неделю: {churn_week}\n"
                f"   📉 Отток за месяц: {churn_month}\n"
                f"   📉 Отток за год: {churn_year}\n"
                f"   🚫 Заблокировали бота: {blocked}"
            )

            return {"STATS_MSG": stats_msg}

        except Exception as e:
            logger.error(
                "Ошибка при получении статистики пользователей",
                error=str(e),
                exc_info=True,
            )
            return {"STATS_MSG": f"❌ Ошибка при загрузке статистики: {str(e)}"}
