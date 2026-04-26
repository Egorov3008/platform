"""Сервис сборки статуса бота для отображения администраторам."""

import time
from typing import Optional, Any

_FUNNEL_NAMES = {
    "key_expiry_24h": "Истечение 24ч",
    "key_expiry_10h": "Истечение 10ч",
    "trial_unused": "Пробный период",
    "cold_lead": "Холодные лиды",
    "referral_bonus": "Реф. бонусы",
    "referral_reminder": "Реф. напоминание",
}

_FUNNEL_ORDER = ["key_expiry_24h", "key_expiry_10h", "trial_unused", "cold_lead", "referral_bonus", "referral_reminder"]


def _format_ago(ts: Optional[float]) -> str:
    if ts is None:
        return "не запускалось"
    delta = time.time() - ts
    if delta < 60:
        return "только что"
    if delta < 3600:
        return f"{int(delta // 60)} мин назад"
    return f"{int(delta // 3600)} ч назад"


def _fmt_rub(amount: Optional[float]) -> str:
    if amount is None:
        return "0 руб"
    return f"{amount:,.0f} руб".replace(",", "\u00a0")


class BotStatusService:
    """Сборка статусного отчёта бота для администраторов."""

    @staticmethod
    async def build_status(
        task_manager: Any,
        cache_storage: Optional[Any],
        cache_service: Optional[Any],
        xui_session: Optional[Any],
        db_conn: Optional[Any],
    ) -> str:
        parts = ["<b>📊 Статус бота</b>\n"]

        # --- Синхронизация ---
        status = task_manager.get_status()
        sync = status["sync"]
        sync_age = _format_ago(sync["last_run"])
        duration_str = f"  |  ⏱ {sync['duration']:.0f} сек" if sync["duration"] else ""
        err_str = f"\n  Ошибок: {sync['error_count']}" if sync["error_count"] else "\n  Ошибок: 0"
        parts.append(
            f"🔄 <b>Синхронизация</b>\n"
            f"  Последний запуск: {sync_age}{duration_str}"
            f"{err_str}"
        )

        # --- Уведомления ---
        notif = status["notifications"]
        notif_enabled = notif.get("enabled", False)
        notif_age = _format_ago(notif["last_run"])
        report = notif["report"]
        enabled_status = "✅ ВКЛ" if notif_enabled else "❌ ВЫКЛ"
        
        if report is not None:
            users_str = f"  |  Пользователей: {report.total_users}"
            funnel_lines = []
            # Заголовок колонок
            funnel_lines.append("  <i>воронка: отправлено / пропущено / ошибки</i>")
            for fid in _FUNNEL_ORDER:
                name = _FUNNEL_NAMES.get(fid, fid)
                stats = report.results_by_funnel.get(fid, {})
                sent = stats.get("sent", 0)
                skipped = stats.get("skipped", 0)
                errors = stats.get("failed_other", 0)
                funnel_lines.append(f"  {name}: {sent} / {skipped} / {errors}")
            # Воронки которых нет в _FUNNEL_ORDER но есть в report
            for fid, stats in report.results_by_funnel.items():
                if fid not in _FUNNEL_ORDER:
                    sent = stats.get("sent", 0)
                    skipped = stats.get("skipped", 0)
                    errors = stats.get("failed_other", 0)
                    funnel_lines.append(f"  {fid}: {sent} / {skipped} / {errors}")
            parts.append(
                f"🔔 <b>Уведомления</b> ({enabled_status})\n"
                f"  Последний цикл: {notif_age}{users_str}\n"
                + "\n".join(funnel_lines)
            )
        else:
            parts.append(
                f"🔔 <b>Уведомления</b> ({enabled_status})\n"
                f"  Последний цикл: {notif_age}"
            )

        # --- Кэш ---
        if cache_storage is not None:
            # Прямой доступ к _storage допустим здесь: только читаем размер namespace,
            # CacheService API не предоставляет метод подсчёта элементов.
            ns_counts = {ns: len(items) for ns, items in cache_storage._storage.items()}
            key_ns = ["users", "keys", "servers", "tariffs", "gift_links", "payments", "referral_links"]
            shown = {k: ns_counts.get(k, 0) for k in key_ns if k in ns_counts or k in ["users", "keys"]}
            cache_lines = []
            row = []
            for ns, count in shown.items():
                row.append(f"{ns}: {count}")
                if len(row) == 3:
                    cache_lines.append("  " + "  |  ".join(row))
                    row = []
            if row:
                cache_lines.append("  " + "  |  ".join(row))
            parts.append("💾 <b>Кэш</b>\n" + "\n".join(cache_lines))
        else:
            parts.append("💾 <b>Кэш</b>\n  Недоступен")

        # --- 3x-ui ---
        if xui_session is not None:
            try:
                t0 = time.monotonic()
                inbounds = await xui_session.get_inbounds()
                latency_ms = round((time.monotonic() - t0) * 1000)
                inbounds_count = len(inbounds) if inbounds else 0
                parts.append(
                    f"🌐 <b>3x-ui Панель</b>\n"
                    f"  ✅ Доступна ({latency_ms} мс)  |  Inbound'ов: {inbounds_count}"
                )
            except Exception as e:
                parts.append(
                    f"🌐 <b>3x-ui Панель</b>\n"
                    f"  ❌ Ошибка: {type(e).__name__}"
                )
        else:
            parts.append("🌐 <b>3x-ui Панель</b>\n  ⚠️ Сессия недоступна")

        # --- Платежи ---
        if db_conn is not None:
            try:
                row = await db_conn.fetchrow("""
                    SELECT
                        COALESCE(SUM(CASE WHEN created_at >= CURRENT_DATE THEN amount ELSE 0 END), 0) AS today,
                        COALESCE(SUM(CASE WHEN created_at >= CURRENT_DATE - INTERVAL '7 days' THEN amount ELSE 0 END), 0) AS week,
                        COALESCE(SUM(CASE WHEN created_at >= CURRENT_DATE - INTERVAL '30 days' THEN amount ELSE 0 END), 0) AS month
                    FROM payments
                    WHERE status = 'succeeded'
                """)
                parts.append(
                    f"💳 <b>Платежи</b> (успешные)\n"
                    f"  Сегодня:  {_fmt_rub(row['today'])}\n"
                    f"  Неделя:   {_fmt_rub(row['week'])}\n"
                    f"  Месяц:    {_fmt_rub(row['month'])}"
                )
            except Exception as e:
                parts.append(f"💳 <b>Платежи</b>\n  ❌ Ошибка: {type(e).__name__}")
        else:
            parts.append("💳 <b>Платежи</b>\n  н/д")

        # --- Рефералы ---
        ref_base = ""
        if cache_service is not None:
            try:
                ref_links = await cache_service.referral_links.all()
                total_links = len(ref_links)
                unique_referrers = len({r.referrer_tg_id for r in ref_links})
                ref_base = f"  Ссылок: {total_links}  |  Рефераторов: {unique_referrers}\n"
            except Exception:
                ref_base = ""

        if db_conn is not None:
            try:
                # Считаем рефералов, оплативших в разные периоды
                row = await db_conn.fetchrow("""
                    SELECT
                        COUNT(DISTINCT CASE WHEN p.created_at >= CURRENT_DATE THEN p.tg_id END) AS paying_today,
                        COUNT(DISTINCT CASE WHEN p.created_at >= CURRENT_DATE - INTERVAL '7 days' THEN p.tg_id END) AS paying_week,
                        COUNT(DISTINCT CASE WHEN p.created_at >= CURRENT_DATE - INTERVAL '30 days' THEN p.tg_id END) AS paying_month
                    FROM payments p
                    JOIN referral_redemptions rr ON rr.referred_tg_id = p.tg_id
                    WHERE p.status = 'succeeded'
                """)
                # Считаем сумму начисленных бонусов реферерам
                bonuses = await db_conn.fetchrow("""
                    SELECT
                        COALESCE(SUM(CASE WHEN awarded_at >= CURRENT_DATE THEN reward_value::REAL ELSE 0 END), 0) AS bonus_today,
                        COALESCE(SUM(CASE WHEN awarded_at >= CURRENT_DATE - INTERVAL '7 days' THEN reward_value::REAL ELSE 0 END), 0) AS bonus_week,
                        COALESCE(SUM(CASE WHEN awarded_at >= CURRENT_DATE - INTERVAL '30 days' THEN reward_value::REAL ELSE 0 END), 0) AS bonus_month
                    FROM referral_rewards
                    WHERE reward_type = 'discount'
                """)
                parts.append(
                    f"👥 <b>Рефералы</b>\n"
                    f"{ref_base}"
                    f"  Рефералы оплатившие / бонусы начислено:\n"
                    f"  Сегодня: {row['paying_today']} чел  |  {_fmt_rub(bonuses['bonus_today'])}\n"
                    f"  Неделя:  {row['paying_week']} чел  |  {_fmt_rub(bonuses['bonus_week'])}\n"
                    f"  Месяц:   {row['paying_month']} чел  |  {_fmt_rub(bonuses['bonus_month'])}"
                )
            except Exception as e:
                parts.append(f"👥 <b>Рефералы</b>\n{ref_base}  ❌ Ошибка: {type(e).__name__}")
        else:
            parts.append(f"👥 <b>Рефералы</b>\n{ref_base}  н/д")

        # --- Подарки ---
        if cache_service is not None:
            try:
                gifts = await cache_service.gifts.all()
                activated = sum(1 for g in gifts if g.recipient_tg_id is not None)
                not_activated = len(gifts) - activated
                parts.append(
                    f"🎁 <b>Подарки</b>\n"
                    f"  Всего: {len(gifts)}  |  Активировано: {activated}  |  Ожидают: {not_activated}"
                )
            except Exception as e:
                parts.append(f"🎁 <b>Подарки</b>\n  ❌ Ошибка: {type(e).__name__}")
        else:
            parts.append("🎁 <b>Подарки</b>\n  н/д")

        # --- Задачи ---
        tasks_alive = status["tasks_alive"]
        if tasks_alive:
            task_strs = [
                f"{name}: {'✅' if alive else '❌'}"
                for name, alive in tasks_alive.items()
            ]
            parts.append("⚙️ <b>Задачи</b>\n  " + "  |  ".join(task_strs))

        return "\n\n".join(parts)
