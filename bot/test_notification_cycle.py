#!/usr/bin/env python3
"""Проверка регистрации воронок."""

from services.notification.routing import KEY_SEGMENT_TO_FUNNEL

print("KEY_SEGMENT_TO_FUNNEL:")
for segment, funnel_id in KEY_SEGMENT_TO_FUNNEL.items():
    print(f"  {segment.name} -> {funnel_id}")

# Обратный маппинг
_SEGMENT_BY_FUNNEL = {v: k for k, v in KEY_SEGMENT_TO_FUNNEL.items()}

print(f"\n_SEGMENT_BY_FUNNEL:")
for funnel_id, segment in _SEGMENT_BY_FUNNEL.items():
    print(f"  {funnel_id} -> {segment.name}")

print("\n\nВоронки, которые должны быть зарегистрированы в tasks.py:")
print("  1. KeyExpiryFunnel24h")
print("  2. KeyExpiryFunnel10h")
print("  3. TrialReminderFunnel")
print("  4. ColdLeadFunnel")
print("  5. ReferralBonusFunnel")
