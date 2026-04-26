"""
Тесты для моделей данных системы уведомлений:
NotificationContext, NotificationResult, FunnelRunReport.
"""

import pytest
from services.notification.models import (
    NotificationResult,
    FunnelRunReport,
    NotificationContext,
)
from models import User, Key
from datetime import datetime, timedelta


def make_user(tg_id: int = 123456) -> User:
    return User(
        tg_id=tg_id,
        created_at=datetime.now() - timedelta(days=7),
    )


def make_key(email: str = "test@example.com") -> Key:
    now_ms = int(datetime.now().timestamp() * 1000)
    return Key(
        tg_id=123456,
        email=email,
        client_id="cli_1",
        expiry_time=now_ms + 24 * 3600 * 1000,
        key="vless://...",
        inbound_id=1,
    )


class TestNotificationContext:
    """Тесты для NotificationContext."""

    def test_fields_accessible(self):
        user = make_user()
        keys = [make_key()]
        segment_keys = [make_key()]
        ctx = NotificationContext(user=user, keys=keys, segment_keys=segment_keys)
        assert ctx.user is user
        assert ctx.keys is keys
        assert ctx.segment_keys is segment_keys

    def test_empty_keys_lists(self):
        user = make_user()
        ctx = NotificationContext(user=user, keys=[], segment_keys=[])
        assert ctx.keys == []
        assert ctx.segment_keys == []


class TestNotificationResult:
    """Тесты для NotificationResult."""

    def test_default_values_are_zero(self):
        result = NotificationResult(tg_id=123456, funnel_id="test_funnel")
        assert result.tg_id == 123456
        assert result.funnel_id == "test_funnel"
        assert result.sent == 0
        assert result.skipped == 0
        assert result.failed_blocked == 0
        assert result.failed_other == 0

    def test_fields_can_be_set_explicitly(self):
        result = NotificationResult(
            tg_id=111,
            funnel_id="funnel_x",
            sent=2,
            skipped=1,
            failed_blocked=1,
            failed_other=3,
        )
        assert result.sent == 2
        assert result.skipped == 1
        assert result.failed_blocked == 1
        assert result.failed_other == 3

    def test_fields_are_mutable(self):
        result = NotificationResult(tg_id=123456, funnel_id="f1")
        result.sent += 1
        result.skipped += 2
        assert result.sent == 1
        assert result.skipped == 2


class TestFunnelRunReport:
    """Тесты для FunnelRunReport."""

    def test_default_values(self):
        report = FunnelRunReport()
        assert report.total_users == 0
        assert report.total_keys_segmented == 0
        assert report.results_by_funnel == {}
        assert report.duration_seconds == 0.0

    def test_add_result_creates_funnel_entry(self):
        report = FunnelRunReport()
        result = NotificationResult(tg_id=1, funnel_id="key_expiry_24h", sent=1)
        report.add_result(result)
        assert "key_expiry_24h" in report.results_by_funnel
        assert report.results_by_funnel["key_expiry_24h"]["sent"] == 1

    def test_add_result_accumulates_sent(self):
        report = FunnelRunReport()
        for i in range(3):
            result = NotificationResult(tg_id=i, funnel_id="f1", sent=1)
            report.add_result(result)
        assert report.results_by_funnel["f1"]["sent"] == 3

    def test_add_result_accumulates_skipped(self):
        report = FunnelRunReport()
        report.add_result(NotificationResult(tg_id=1, funnel_id="f1", skipped=2))
        report.add_result(NotificationResult(tg_id=2, funnel_id="f1", skipped=3))
        assert report.results_by_funnel["f1"]["skipped"] == 5

    def test_add_result_accumulates_failed_blocked(self):
        report = FunnelRunReport()
        report.add_result(NotificationResult(tg_id=1, funnel_id="f1", failed_blocked=1))
        report.add_result(NotificationResult(tg_id=2, funnel_id="f1", failed_blocked=1))
        assert report.results_by_funnel["f1"]["failed_blocked"] == 2

    def test_add_result_accumulates_failed_other(self):
        report = FunnelRunReport()
        report.add_result(NotificationResult(tg_id=1, funnel_id="f1", failed_other=3))
        assert report.results_by_funnel["f1"]["failed_other"] == 3

    def test_add_result_multiple_funnels(self):
        report = FunnelRunReport()
        report.add_result(NotificationResult(tg_id=1, funnel_id="f1", sent=1))
        report.add_result(NotificationResult(tg_id=1, funnel_id="f2", sent=2))
        report.add_result(
            NotificationResult(tg_id=2, funnel_id="f1", sent=3, skipped=1)
        )
        assert report.results_by_funnel["f1"]["sent"] == 4
        assert report.results_by_funnel["f1"]["skipped"] == 1
        assert report.results_by_funnel["f2"]["sent"] == 2

    def test_add_result_initialises_all_stat_keys(self):
        report = FunnelRunReport()
        report.add_result(NotificationResult(tg_id=1, funnel_id="new_funnel"))
        stats = report.results_by_funnel["new_funnel"]
        assert set(stats.keys()) == {
            "sent",
            "skipped",
            "failed_blocked",
            "failed_other",
        }

    def test_duration_seconds_is_mutable(self):
        report = FunnelRunReport()
        report.duration_seconds = 3.14
        assert report.duration_seconds == pytest.approx(3.14)
