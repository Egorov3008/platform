"""Геттер окна конверсий для admin-панели."""

from typing import Any, Dict

import asyncpg
from aiogram_dialog import DialogManager

from dialogs.windows.base import DataGetter
from logger import logger
from services.analytics.conversions import ConversionMetrics, ConversionMetricsService
from services.analytics.dashboard_metrics import DashboardMetrics, DashboardMetricsService
from services.cache.service import CacheService


def _fmt(metrics: ConversionMetrics) -> str:
    m = metrics

    tariff_lines = "\n".join(
        f"      {i}. {s.tariff_name}: <b>{s.payment_count} ключей</b> · {s.total_amount:,.0f} ₽"
        for i, s in enumerate(m.tariff_stats, 1)
    ) or "      Нет данных"

    return (
        f"📊 <b>Аналитика за {m.year} год</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"

        "👥 <b>База пользователей</b>\n"
        f"   Всего: <b>{m.total_users}</b> · "
        f"с ключами: <b>{m.users_with_keys}</b> · "
        f"с активными: <b>{m.users_with_active_keys}</b>\n"
        f"   Активные ключи: <b>{m.paid_keys_active}</b> платных + "
        f"<b>{m.trial_keys_active}</b> trial\n\n"

        "📅 <b>Регистрации</b>\n"
        f"   За год: <b>{m.registered_this_year}</b> · "
        f"за месяц: <b>{m.registered_this_month}</b> · "
        f"за неделю: <b>{m.registered_this_week}</b>\n\n"

        f"🔁 <b>Воронка конверсий {m.year}</b>\n"
        f"   Новые пользователи: <b>{m.registered_this_year}</b>\n"
        f"   → Запустили trial: <b>{m.trial_activated_this_year}</b> "
        f"(<b>{m.reg_to_trial_pct}%</b>)\n"
        f"   → Оплатили после trial: <b>{m.trial_to_paid_this_year}</b> "
        f"(<b>{m.trial_to_paid_pct}%</b> от trial)\n"
        f"   → Повторная оплата: <b>{m.repeat_payers_this_year}</b> из "
        f"<b>{m.payers_this_year}</b> "
        f"(<b>{m.retention_pct}%</b>)\n"
        f"   Итоговая конверсия новых: <b>{m.overall_conversion_pct}%</b>\n\n"

        "📢 <b>Каналы привлечения</b>\n"
        f"   Рефералы: пришло <b>{m.referred_this_year}</b>, "
        f"оплатили <b>{m.referred_paid_this_year}</b> "
        f"(<b>{m.referral_pct}%</b>)\n"
        f"   Подарки: создано <b>{m.gifts_this_year}</b>, "
        f"активировано <b>{m.gifts_activated_this_year}</b> "
        f"(<b>{m.gift_pct}%</b>)\n\n"

        f"💳 <b>Топ тарифов {m.year}</b> — "
        f"выручка <b>{m.total_revenue_this_year:,.0f} ₽</b>\n"
        f"{tariff_lines}"
    )


class AdminConversionsGetter(DataGetter):
    """Собирает метрики конверсий через SQL-агрегаты для отображения в admin-панели.

    Использует ConversionMetricsService с CTE-запросами для эффективного
    расчёта метрик напрямую из БД.
    """

    def __init__(
        self,
        db_pool: asyncpg.Pool,
        cache_service: CacheService,
    ) -> None:
        self._db_pool = db_pool
        self._cache_service = cache_service

    async def get_data(self, dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
        try:
            # Получаем метрики конверсий
            conv_service = ConversionMetricsService(self._db_pool)
            conv_metrics = await conv_service.get_cached(
                self._cache_service, ttl_seconds=300
            )

            # Получаем dashboard-метрики
            dash_service = DashboardMetricsService(self._db_pool)
            dash_metrics = await dash_service.get_cached(
                self._cache_service, ttl_seconds=300
            )

            return {
                "CONVERSIONS_MSG": _fmt(conv_metrics),
                "DASHBOARD_MSG": _fmt_dashboard(dash_metrics),
            }
        except Exception as e:
            logger.error("Ошибка при расчёте конверсий", error=str(e), exc_info=True)
            return {
                "CONVERSIONS_MSG": f"❌ Ошибка при загрузке конверсий: {e}",
                "DASHBOARD_MSG": f"❌ Ошибка при загрузке dashboard: {e}",
            }


def _fmt_dashboard(metrics: DashboardMetrics) -> str:
    """Форматирует dashboard-метрики для вывода."""
    # MRR блок
    mrr_block = (
        f"💰 <b>MRR (Monthly Recurring Revenue)</b>\n"
        f"   Текущий месяц: <b>{metrics.mrr_current_month:,.0f} ₽</b>\n"
        f"   Прошлый месяц: <b>{metrics.mrr_previous_month:,.0f} ₽</b>\n"
        f"   Рост: <b>{metrics.mrr_growth:+.1f}%</b>\n"
        f"   Платящих пользователей: <b>{metrics.paying_users_current}</b>\n"
        f"   ARPU: <b>{metrics.arpu_current:,.0f} ₽</b>\n\n"
    )

    # Воронка за 30 дней
    funnel_block = (
        f"📊 <b>Воронка за 30 дней</b>\n"
        f"   Новые пользователи: <b>{metrics.total_new_users_30d}</b>\n"
        f"   С ключами: <b>{metrics.total_users_with_keys_30d}</b> "
        f"(<b>{metrics.conversion_to_keys_pct:.1f}%</b>)\n"
        f"   Платящих: <b>{metrics.total_paying_users_30d}</b> "
        f"(<b>{metrics.conversion_to_paid_pct:.1f}%</b>)\n\n"
    )

    # Истекающие ключи
    expiring_lines = "\n".join(
        f"   {k.expiry_range}: <b>{k.keys_count}</b> ключ."
        for k in metrics.expiring_keys
    ) or "   Нет истекающих ключей"

    expiry_block = (
        f"⏰ <b>Истекающие ключи</b>\n"
        f"   Всего за 72 часа: <b>{metrics.total_expiring_72h}</b>\n"
        f"{expiring_lines}\n\n"
    )

    # Платежи
    payment_lines = "\n".join(
        f"   {p.status}: <b>{p.count}</b> ({p.total_amount:,.0f} ₽)"
        for p in metrics.payment_statuses
    ) or "   Нет платежей"

    payment_block = (
        f"💳 <b>Платежи (за год)</b>\n"
        f"   Успешных: <b>{metrics.succeeded_pct:.1f}%</b>\n"
        f"{payment_lines}\n"
    )

    return mrr_block + funnel_block + expiry_block + payment_block
