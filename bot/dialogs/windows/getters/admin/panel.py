from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Tuple, cast

from aiogram_dialog import DialogManager

from dialogs.windows.base import DataGetter
from models import Key, User
from services.core.data.service import ServiceDataModel
from logger import logger


class AdminStatsGetter(DataGetter):
    """Получает статистику пользователей: регистрации, отток, заблокированные."""

    def __init__(self, model_data: ServiceDataModel):
        self.users = model_data.users
        self.keys = model_data.keys

    # ------------------------------------------------------------------
    # Вспомогательные методы
    # ------------------------------------------------------------------

    @staticmethod
    def _get_week_boundaries(now: datetime) -> Tuple[datetime, datetime]:
        """Возвращает (start, end) текущей недели: понедельник 00:00 — воскресенье 23:59 UTC."""
        # weekday(): Monday=0 … Sunday=6
        days_since_monday = now.weekday()
        monday = now.replace(
            hour=0, minute=0, second=0, microsecond=0
        ) - timedelta(days=days_since_monday)
        sunday = monday.replace(hour=23, minute=59, second=59) + timedelta(days=6)
        return monday, sunday

    @staticmethod
    def _count_registrations(
        users: List[User], start: datetime, end: datetime
    ) -> int:
        """Считает пользователей, зарегистрированных в [start, end]."""
        count = 0
        for u in users:
            created = u.created_at
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            if start <= created <= end:
                count += 1
        return count

    async def _count_churn(
        self, users: List[User], keys: List[Key], start: datetime, end: datetime
    ) -> int:
        """
        Считает пользователей в оттоке.
        Отток — пользователь, у которого ВСЕ ключи истекли в периоде
        и при этом нет ни одного активного ключа.
        """
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        start_ms = int(start.timestamp() * 1000)
        end_ms = int(end.timestamp() * 1000)

        # Группируем ключи по tg_id
        keys_by_user: Dict[int, List[Key]] = {}
        for k in keys:
            keys_by_user.setdefault(k.tg_id, []).append(k)

        churned = 0
        for u in users:
            user_keys = keys_by_user.get(u.tg_id, [])
            if not user_keys:
                # У пользователя нет ключей — не считаем оттоком
                # (он просто ещё не покупал)
                continue

            all_expired = all(k.expiry_time < now_ms for k in user_keys)
            if not all_expired:
                # Есть хотя бы один активный ключ — не отток
                continue

            # Проверяем, что все ключи истекли в пределах периода
            all_in_period = all(start_ms <= k.expiry_time <= end_ms for k in user_keys)
            if all_in_period:
                churned += 1

        return churned

    @staticmethod
    def _count_blocked(users: List[User]) -> int:
        """Считает пользователей с is_blocked == True."""
        return sum(1 for u in users if u.is_blocked)

    # ------------------------------------------------------------------
    # Основной метод
    # ------------------------------------------------------------------

    async def get_data(self, dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
        """Собирает статистику пользователей."""
        try:
            all_users = await self.users.get_all()
            all_keys = await self.keys.get_all()

            if not isinstance(all_users, list):
                all_users = [all_users] if all_users else []
            users_list: List[User] = cast(List[User], all_users)

            if not isinstance(all_keys, list):
                all_keys = [all_keys] if all_keys else []
            keys_list: List[Key] = cast(List[Key], all_keys)

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
