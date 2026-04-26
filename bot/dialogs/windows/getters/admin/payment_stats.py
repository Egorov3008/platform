"""Getter для статистики платежей и прогноза выручки."""

from datetime import datetime
from typing import Dict, Any

import asyncpg
from aiogram_dialog import DialogManager

from dialogs.windows.base import DataGetter
from logger import logger
from services.analytics.payment_metrics import PaymentMetricsService


class PaymentStatsGetter(DataGetter):
    """Собирает статистику платежей и формирует прогноз выручки."""

    def __init__(self, payment_metrics: PaymentMetricsService) -> None:
        self._payment_metrics = payment_metrics

    async def get_data(self, dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
        """Собирает статистику платежей и прогнозы."""
        try:
            # Получаем статистику выручки
            revenue_stats = await self._payment_metrics.get_revenue_stats()

            # Получаем прогноз
            forecast = await self._payment_metrics.forecast_revenue()

            # Форматируем сообщение
            stats_msg = self._format_stats(revenue_stats, forecast)

            # Сохраняем данные для возможных использований
            dialog_manager.dialog_data["revenue_stats"] = {
                "year_total": revenue_stats.year_total,
                "month_total": revenue_stats.month_total,
                "week_total": revenue_stats.week_total,
                "day_total": revenue_stats.day_total,
                "year_payments": revenue_stats.year_payments_count,
                "month_payments": revenue_stats.month_payments_count,
                "week_payments": revenue_stats.week_payments_count,
                "day_payments": revenue_stats.day_payments_count,
            }
            dialog_manager.dialog_data["forecast"] = {
                "week_forecast": forecast.week_forecast,
                "week_confidence": forecast.week_confidence,
                "month_forecast": forecast.month_forecast,
                "month_confidence": forecast.month_confidence,
                "growth_trend": forecast.growth_trend,
            }
            dialog_manager.dialog_data["last_updated"] = datetime.now().strftime(
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
    def _format_stats(revenue_stats, forecast) -> str:
        """Форматирует статистику и прогноз в читаемое сообщение."""
        msg = "💰 <b>Статистика платежей</b>\n\n"

        # Выручка
        msg += "📊 <b>Выручка:</b>\n"
        msg += f"   📅 За год: {revenue_stats.year_total:,.2f} ₽ ({revenue_stats.year_payments_count} плат.)\n"
        msg += f"   🗓️ За месяц: {revenue_stats.month_total:,.2f} ₽ ({revenue_stats.month_payments_count} плат.)\n"
        msg += f"   📆 За неделю: {revenue_stats.week_total:,.2f} ₽ ({revenue_stats.week_payments_count} плат.)\n"
        msg += f"   ☀️ За сегодня: {revenue_stats.day_total:,.2f} ₽ ({revenue_stats.day_payments_count} плат.)\n"

        # Средние чеки
        if revenue_stats.avg_payment_month > 0:
            msg += f"\n   💳 Средний чек (мес): {revenue_stats.avg_payment_month:,.2f} ₽\n"

        msg += "\n"

        # Прогноз
        msg += "🔮 <b>Прогноз выручки:</b>\n"

        if forecast.week_forecast > 0:
            confidence_emoji = "🟢" if forecast.week_confidence > 70 else "🟡" if forecast.week_confidence > 40 else "🔴"
            msg += f"   {confidence_emoji} Следующая неделя: {forecast.week_forecast:,.2f} ₽ ({forecast.week_confidence:.0f}%)\n"
            if forecast.week_method != "none":
                method_names = {
                    "combined": "комбинированный",
                    "moving_avg": "скользящее среднее",
                    "linear_regression": "линейная регрессия",
                    "insufficient_data": "недостаточно данных",
                }
                method_name = method_names.get(forecast.week_method, forecast.week_method)
                msg += f"      Метод: {method_name}\n"

        if forecast.month_forecast > 0:
            confidence_emoji = "🟢" if forecast.month_confidence > 70 else "🟡" if forecast.month_confidence > 40 else "🔴"
            msg += f"   {confidence_emoji} Следующий месяц: {forecast.month_forecast:,.2f} ₽ ({forecast.month_confidence:.0f}%)\n"
            if forecast.month_method != "none":
                method_names = {
                    "combined": "комбинированный",
                    "moving_avg": "скользящее среднее",
                    "linear_regression": "линейная регрессия",
                    "insufficient_data": "недостаточно данных",
                }
                method_name = method_names.get(forecast.month_method, forecast.month_method)
                msg += f"      Метод: {method_name}\n"

        if forecast.week_forecast == 0 and forecast.month_forecast == 0:
            msg += "   ⚠️ Недостаточно данных для прогноза\n"

        # Тренд
        if forecast.growth_trend != 0:
            trend_icon = "📈" if forecast.growth_trend > 0 else "📉"
            msg += f"\n{trend_icon} <b>Тренд:</b> {forecast.growth_trend:+.1f}%\n"

        # Исторические данные
        if forecast.last_4_weeks_avg > 0:
            msg += f"\n📊 <b>Справочно:</b>\n"
            msg += f"   Среднее за 4 недели: {forecast.last_4_weeks_avg:,.2f} ₽\n"
        if forecast.last_3_months_avg > 0:
            msg += f"   Среднее за 3 месяца: {forecast.last_3_months_avg:,.2f} ₽\n"

        return msg
