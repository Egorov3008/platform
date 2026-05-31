"""Геттер для отображения платежей за текущие сутки с проверкой ключей."""

from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from aiogram_dialog import DialogManager

from api.backend_client import BackendAPIClient
from dialogs.windows.base import DataGetter
from models import Key, PaymentModel
from logger import logger


class RecentPaymentsGetter(DataGetter):
    """Получает платежи за сегодня с проверкой статуса связанных ключей через backend API."""

    def __init__(self, backend_client: BackendAPIClient):
        self._backend = backend_client

    def _parse_payment_type(self, payment_type: Optional[str]) -> tuple[str, str]:
        if not payment_type:
            return "unknown", ""
        parts = payment_type.split("|", 1)
        return parts[0], parts[1] if len(parts) > 1 else ""

    def _check_key_status(self, key: Optional[Key], now_ms: int) -> str:
        if not key:
            return "⚠️ Ключ не найден"
        if key.expiry_time > now_ms:
            return f"✅ Ключ активен до {key.warp_expiry_time}"
        return f"❌ Ключ истёк {key.warp_expiry_time}"

    def _find_key_for_create(
        self,
        tg_id: Optional[int],
        tariff_id_str: str,
        keys_by_tg: Dict[int, List[Key]],
    ) -> Optional[Key]:
        if not tg_id:
            return None
        user_keys = keys_by_tg.get(tg_id, [])
        try:
            tid = int(tariff_id_str) if tariff_id_str else None
        except (ValueError, TypeError):
            tid = None
        if tid is not None:
            for k in user_keys:
                if k.tariff_id == tid:
                    return k
        return user_keys[0] if user_keys else None

    async def get_data(self, dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
        try:
            all_payments_raw = await self._backend.admin_list_payments()
            raw_keys = await self._backend.admin_list_keys()
            all_keys = [Key.from_backend(k) for k in raw_keys]
            all_tariffs_raw = await self._backend.admin_list_tariffs()

            all_payments = []
            for p in all_payments_raw:
                if isinstance(p, dict):
                    all_payments.append(PaymentModel(**p))
                elif isinstance(p, PaymentModel):
                    all_payments.append(p)

            all_tariffs = []
            for t in all_tariffs_raw:
                if isinstance(t, dict):
                    from models import Tariff
                    all_tariffs.append(Tariff(**t))
                elif hasattr(t, "id"):
                    all_tariffs.append(t)

            keys_by_email: Dict[str, Key] = {k.email: k for k in all_keys}
            keys_by_tg: Dict[int, List[Key]] = defaultdict(list)
            for k in all_keys:
                keys_by_tg[k.tg_id].append(k)
            tariffs_by_id = {t.id: t for t in all_tariffs}

            now = datetime.now(timezone.utc)
            today = now.date()
            now_ms = int(now.timestamp() * 1000)

            today_payments: List[PaymentModel] = []
            for p in all_payments:
                created = p.created_at
                if created is None:
                    continue
                if created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)
                if created.date() == today:
                    today_payments.append(p)

            today_payments.sort(key=lambda p: p.created_at, reverse=True)

            if not today_payments:
                return {
                    "RECENT_PAY_MSG": f"💳 Платежи за сегодня ({today.strftime('%d.%m.%Y')}):\n\nПлатежей не найдено.",
                    "payments_data": [],
                }

            total_amount = sum(p.amount for p in today_payments if p.amount and p.status == "succeeded")
            lines = [
                f"💳 Платежи за сегодня ({today.strftime('%d.%m.%Y')}):\n",
                f"📊 Всего: {len(today_payments)} на сумму {total_amount:.0f} ₽\n",
            ]

            payment_keys: Dict[str, Key] = {}
            payments_data = []

            for i, p in enumerate(today_payments):
                created = p.created_at
                if created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)
                time_str = created.strftime("%H:%M")

                operation, data = self._parse_payment_type(p.payment_type)

                status_map = {"succeeded": "✅", "canceled": "❌", "pending": "⏳"}
                status_icon = status_map.get(p.status, "❓")
                status_suffix = ""
                if p.status == "canceled":
                    status_suffix = " (отменён)"
                elif p.status == "pending":
                    status_suffix = " (ожидание)"

                amount_str = f"{p.amount:.0f}" if p.amount else "0"

                found_key: Optional[Key] = None
                if operation == "renew_key":
                    op_label = "🔄 Продление"
                    op_detail = f" | {data}" if data else ""
                    found_key = keys_by_email.get(data)
                elif operation == "create_key":
                    op_label = "🔑 Создание ключа"
                    tariff = tariffs_by_id.get(int(data)) if data.isdigit() else None
                    tariff_name = tariff.name_tariff if tariff else data
                    op_detail = f" | Тариф: {tariff_name}"
                    found_key = self._find_key_for_create(p.tg_id, data, keys_by_tg)
                else:
                    op_label = f"❓ {operation}"
                    op_detail = f" | {data}" if data else ""

                key_status = self._check_key_status(
                    found_key if p.status == "succeeded" else None,
                    now_ms,
                )
                if p.status != "succeeded":
                    key_status = "⚠️ Ключ не создан" if operation == "create_key" else "⚠️ Не обработан"

                lines.append(
                    f"{i + 1}. {time_str} | {status_icon} {amount_str}₽{status_suffix}\n"
                    f"   {op_label}{op_detail}\n"
                    f"   👤 tg: {p.tg_id}\n"
                    f"   📋 Результат: {key_status}"
                )

                if found_key:
                    idx_str = str(i)
                    payment_keys[idx_str] = found_key
                    payments_data.append((f"🔍 {i + 1}. {found_key.email}", idx_str))

            dialog_manager.dialog_data["payment_keys"] = payment_keys

            return {
                "RECENT_PAY_MSG": "\n".join(lines),
                "payments_data": payments_data,
            }

        except Exception as e:
            logger.error(
                "Ошибка при получении платежей за сегодня",
                error=str(e),
                exc_info=True,
            )
            return {
                "RECENT_PAY_MSG": f"❌ Ошибка при загрузке платежей: {str(e)}",
                "payments_data": [],
            }
