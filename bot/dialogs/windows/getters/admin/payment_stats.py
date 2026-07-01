"""Getter для статистики платежей через backend API."""

from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List

from aiogram_dialog import DialogManager

from api.backend_client import BackendAPIClient
from dialogs.windows.base import DataGetter
from logger import logger


class PaymentStatsGetter(DataGetter):
    """Собирает статистику платежей из backend API."""

    def __init__(self, backend: BackendAPIClient) -> None:
        self._backend = backend

    async def get_data(self, dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
        """Собирает статистику платежей и формирует прогноз выручки."""
        try:
            payments = await self._backend.admin_list_payments()
            stats = self._calculate_stats(payments)
            forecast = self._calculate_forecast(payments)
            stats_msg = self._format_stats(stats, forecast)

            dialog_manager.dialog_data["revenue_stats"] = {
                "year_total": stats["year_total"],
                "month_total": stats["month_total"],
                "week_total": stats["week_total"],
                "day_total": stats["day_total"],
                "year_payments": stats["year_payments"],
                "month_payments": stats["month_payments"],
                "week_payments": stats["week_payments"],
                "day_payments": stats["day_payments"],
            }
            dialog_manager.dialog_data["forecast"] = forecast
            dialog_manager.dialog_data["last_updated"] = datetime.now(timezone.utc).strftime(
                "%d.%m.%Y %H:%M"
            )

            return {"PAYMENT_STATS_MSG": stats_msg}
        except Exception as e:
            logger.error(
                "Ошибка при получении статистики платежей",
                error=str(e),
                exc_info=True,
            )
            return {"PAYMENT_STATS_MSG": f"❌ Ошибка при загрузке статистики: {e}"}

    @staticmethod
    def _calculate_stats(payments: List[dict]) -> dict:
        now = datetime.now(timezone.utc)
        year_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        # Week starts on Monday
        week_start = (now - timedelta(days=now.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        succeeded = [p for p in payments if p.get("status") == "succeeded"]

        def total_since(cutoff: datetime) -> tuple[float, int]:
            filtered = [
                p for p in succeeded
                if _parse_dt(p.get("created_at")) and _parse_dt(p.get("created_at")) >= cutoff
            ]
            total = sum(float(p.get("amount", 0)) for p in filtered)
            return total, len(filtered)

        year_total, year_count = total_since(year_start)
        month_total, month_count = total_since(month_start)
        week_total, week_count = total_since(week_start)
        day_total, day_count = total_since(day_start)

        return {
            "year_total": year_total,
            "year_payments": year_count,
            "month_total": month_total,
            "month_payments": month_count,
            "week_total": week_total,
            "week_payments": week_count,
            "day_total": day_total,
            "day_payments": day_count,
        }

    @staticmethod
    def _calculate_forecast(payments: List[dict]) -> dict:
        """Простой прогноз на основе средних за последние 4 недели и 3 месяца."""
        now = datetime.now(timezone.utc)
        succeeded = [p for p in payments if p.get("status") == "succeeded"]

        # Weekly buckets
        weekly_totals: dict[int, float] = {}
        for p in succeeded:
            dt = _parse_dt(p.get("created_at"))
            if not dt:
                continue
            days_ago = (now - dt).days
            week_ago = days_ago // 7
            if week_ago < 8:
                weekly_totals.setdefault(week_ago, 0.0)
                weekly_totals[week_ago] += float(p.get("amount", 0))

        recent_weeks = [weekly_totals.get(w, 0.0) for w in range(4)]
        week_forecast = sum(recent_weeks) / max(len([x for x in recent_weeks if x > 0]), 1)

        # Monthly buckets
        monthly_totals: dict[int, float] = {}
        for p in succeeded:
            dt = _parse_dt(p.get("created_at"))
            if not dt:
                continue
            months_ago = (now.year - dt.year) * 12 + (now.month - dt.month)
            if months_ago < 6:
                monthly_totals.setdefault(months_ago, 0.0)
                monthly_totals[months_ago] += float(p.get("amount", 0))

        recent_months = [monthly_totals.get(m, 0.0) for m in range(3)]
        month_forecast = sum(recent_months) / max(len([x for x in recent_months if x > 0]), 1)

        return {
            "week_forecast": round(week_forecast, 2),
            "week_confidence": min(95.0, max(10.0, len([x for x in recent_weeks if x > 0]) * 25)),
            "month_forecast": round(month_forecast, 2),
            "month_confidence": min(95.0, max(10.0, len([x for x in recent_months if x > 0]) * 30)),
            "growth_trend": 0.0,
        }

    @staticmethod
    def _format_stats(stats: dict, forecast: dict) -> str:
        msg = "💰 <b>Статистика платежей</b>\n\n"
        msg += "📊 <b>Выручка:</b>\n"
        msg += f"   📅 За год: {stats['year_total']:,.2f} ₽ ({stats['year_payments']} плат.)\n"
        msg += f"   🗓️ За месяц: {stats['month_total']:,.2f} ₽ ({stats['month_payments']} плат.)\n"
        msg += f"   📆 За неделю: {stats['week_total']:,.2f} ₽ ({stats['week_payments']} плат.)\n"
        msg += f"   ☀️ За сегодня: {stats['day_total']:,.2f} ₽ ({stats['day_payments']} плат.)\n"
        msg += "\n🔮 <b>Прогноз выручки:</b>\n"
        if forecast["week_forecast"] > 0:
            msg += f"   Следующая неделя: {forecast['week_forecast']:,.2f} ₽\n"
        if forecast["month_forecast"] > 0:
            msg += f"   Следующий месяц: {forecast['month_forecast']:,.2f} ₽\n"
        if forecast["week_forecast"] == 0 and forecast["month_forecast"] == 0:
            msg += "   ⚠️ Недостаточно данных для прогноза\n"
        return msg


def _parse_dt(value) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:
            return None
    return None
