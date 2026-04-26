"""
Tests for KeyStatsGetter.

KeyStatsGetter.get_data() fetches all keys, produces:
1. Overall statistics for ALL keys with per-tariff-name breakdown
2. 24h expiring keys with per-tariff-name breakdown
3. Notification stats for 24h keys

Only model_data.keys.get_all() and model_data.tariffs.get_data() are mocked.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from models import Key, Tariff
from dialogs.windows.getters.admin.key_stats import KeyStatsGetter


def make_key(
    email: str,
    tg_id: int,
    expiry_offset_ms: int,
    tariff_id: int = 20,
    used_traffic: float = 1000,
    notified_10h: bool = False,
    notified_24h: bool = False,
) -> Key:
    """Build a Key with specified parameters."""
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    return Key(
        email=email,
        tg_id=tg_id,
        client_id="c1",
        key="k",
        inbound_id=1,
        expiry_time=now_ms + expiry_offset_ms,
        tariff_id=tariff_id,
        used_traffic=used_traffic,
        notified_10h=notified_10h,
        notified_24h=notified_24h,
    )


def make_tariff(tariff_id: int, name: str) -> Tariff:
    """Создаёт тестовый тариф."""
    return Tariff(
        id=tariff_id,
        name_tariff=name,
        amount=100.0,
        limit_ip=1,
        period=30,
    )


@pytest.fixture
def mock_dialog_manager():
    """Mock DialogManager with writable dialog_data."""
    manager = AsyncMock()
    manager.dialog_data = {}
    manager.start_data = {}
    manager.middleware_data = {}
    return manager


@pytest.fixture
def mock_model_data():
    """Mock ServiceDataModel with keys and tariffs."""
    model_data = AsyncMock()
    model_data.keys = AsyncMock()
    model_data.tariffs = AsyncMock()
    model_data.tariffs.get_data = AsyncMock(return_value=None)
    return model_data


# ============================================================================
# Тесты базовой функциональности
# ============================================================================


class TestKeyStatsGetterBasic:
    """Базовые тесты KeyStatsGetter."""

    @pytest.mark.asyncio
    async def test_returns_stats_msg(self, mock_model_data, mock_dialog_manager):
        """KeyStatsGetter должен вернуть STATS_MSG."""
        mock_model_data.keys.get_all.return_value = []
        getter = KeyStatsGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)
        assert "STATS_MSG" in result
        assert "Статистика ключей" in result["STATS_MSG"]

    @pytest.mark.asyncio
    async def test_returns_stats_dict(self, mock_model_data, mock_dialog_manager):
        """KeyStatsGetter должен вернуть stats dict."""
        mock_model_data.keys.get_all.return_value = []
        getter = KeyStatsGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)
        assert "stats" in result
        assert isinstance(result["stats"], dict)

    @pytest.mark.asyncio
    async def test_empty_keys_returns_zero_stats(self, mock_model_data, mock_dialog_manager):
        """При пустом списке ключей статистика должна быть нулевой."""
        mock_model_data.keys.get_all.return_value = []
        getter = KeyStatsGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)

        stats = result["stats"]
        assert stats["all_total"] == 0
        assert stats["all_trial"] == 0
        assert stats["all_paid"] == 0
        assert stats["all_unused"] == 0
        assert stats["expiring_24h_total"] == 0
        assert stats["all_trial_by_tariff"] == {}
        assert stats["all_paid_by_tariff"] == {}
        assert stats["all_unused_by_tariff"] == {}

    @pytest.mark.asyncio
    async def test_saves_data_to_dialog_data(self, mock_model_data, mock_dialog_manager):
        """KeyStatsGetter должен сохранить данные в dialog_data."""
        mock_model_data.keys.get_all.return_value = []
        getter = KeyStatsGetter(mock_model_data)
        await getter.get_data(mock_dialog_manager)
        assert "stats" in mock_dialog_manager.dialog_data
        assert "all_keys" in mock_dialog_manager.dialog_data
        assert "expiring_24h_keys" in mock_dialog_manager.dialog_data


# ============================================================================
# Тесты общей статистики всех ключей
# ============================================================================


class TestKeyStatsGetterAllKeys:
    """Тесты общей статистики всех ключей."""

    @pytest.mark.asyncio
    async def test_all_total_count(self, mock_model_data, mock_dialog_manager):
        """Общее количество ключей должно быть корректным."""
        keys = [
            make_key("k1@test.com", 1, 72 * 3600 * 1000),
            make_key("k2@test.com", 2, 48 * 3600 * 1000),
            make_key("k3@test.com", 3, 24 * 3600 * 1000),
        ]
        mock_model_data.keys.get_all.return_value = keys
        getter = KeyStatsGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)

        assert result["stats"]["all_total"] == 3

    @pytest.mark.asyncio
    async def test_all_paid_with_tariff_names(self, mock_model_data, mock_dialog_manager):
        """Платные ключи должны группироваться по названиям тарифов (все, не только 24h)."""
        keys = [
            make_key("p1@test.com", 1, 72 * 3600 * 1000, tariff_id=2),
            make_key("p2@test.com", 2, 48 * 3600 * 1000, tariff_id=2),
            make_key("p3@test.com", 3, 5 * 3600 * 1000, tariff_id=5),
        ]
        mock_model_data.keys.get_all.return_value = keys

        async def mock_get_data(tid):
            tariff_map = {
                2: make_tariff(2, "1 месяц"),
                5: make_tariff(5, "3 месяца"),
            }
            return tariff_map.get(tid)

        mock_model_data.tariffs.get_data.side_effect = mock_get_data
        getter = KeyStatsGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)

        assert result["stats"]["all_paid"] == 3
        assert result["stats"]["all_paid_by_tariff"] == {
            "1 месяц": 2,
            "3 месяца": 1,
        }

    @pytest.mark.asyncio
    async def test_all_trial_with_tariff_name(self, mock_model_data, mock_dialog_manager):
        """Trial ключи должны группироваться по названию тарифа (все, не только 24h)."""
        keys = [
            make_key("t1@test.com", 1, 72 * 3600 * 1000, tariff_id=10),
            make_key("t2@test.com", 2, 48 * 3600 * 1000, tariff_id=10),
        ]
        mock_model_data.keys.get_all.return_value = keys
        mock_model_data.tariffs.get_data.return_value = make_tariff(10, "Trial")

        getter = KeyStatsGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)

        assert result["stats"]["all_trial"] == 2
        assert result["stats"]["all_trial_by_tariff"] == {"Trial": 2}

    @pytest.mark.asyncio
    async def test_all_unused_by_tariff(self, mock_model_data, mock_dialog_manager):
        """Неиспользуемые ключи должны группироваться по названиям тарифов (все, не только 24h)."""
        keys = [
            make_key("u1@test.com", 1, 72 * 3600 * 1000, tariff_id=2, used_traffic=0),
            make_key("u2@test.com", 2, 48 * 3600 * 1000, tariff_id=5, used_traffic=0),
            make_key("used@test.com", 3, 24 * 3600 * 1000, tariff_id=2, used_traffic=5000),
        ]
        mock_model_data.keys.get_all.return_value = keys

        async def mock_get_data(tid):
            tariff_map = {
                2: make_tariff(2, "1 месяц"),
                5: make_tariff(5, "3 месяца"),
            }
            return tariff_map.get(tid)

        mock_model_data.tariffs.get_data.side_effect = mock_get_data
        getter = KeyStatsGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)

        assert result["stats"]["all_unused"] == 2
        assert result["stats"]["all_unused_by_tariff"] == {
            "1 месяц": 1,
            "3 месяца": 1,
        }


# ============================================================================
# Тесты 24h разбивки
# ============================================================================


class TestKeyStatsGetter24hBreakdown:
    """Тесты 24h разбивки."""

    @pytest.mark.asyncio
    async def test_expiring_24h_count(self, mock_model_data, mock_dialog_manager):
        """Должны учитываться только ключи, истекающие в ближайшие 24h."""
        keys = [
            make_key("expired@test.com", 1, -1000),
            make_key("expiring_1h@test.com", 2, 1 * 3600 * 1000),
            make_key("expiring_12h@test.com", 3, 12 * 3600 * 1000),
            make_key("expiring_23h@test.com", 4, 23 * 3600 * 1000),
            make_key("expiring_48h@test.com", 5, 48 * 3600 * 1000),
        ]
        mock_model_data.keys.get_all.return_value = keys
        getter = KeyStatsGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)

        assert result["stats"]["all_total"] == 5
        assert result["stats"]["expiring_24h_total"] == 3

    @pytest.mark.asyncio
    async def test_24h_paid_with_tariff_names(self, mock_model_data, mock_dialog_manager):
        """24h платные ключи должны группироваться по названиям тарифов."""
        keys = [
            make_key("p1@test.com", 1, 5 * 3600 * 1000, tariff_id=2),
            make_key("p2@test.com", 2, 10 * 3600 * 1000, tariff_id=5),
        ]
        mock_model_data.keys.get_all.return_value = keys

        async def mock_get_data(tid):
            tariff_map = {
                2: make_tariff(2, "1 месяц"),
                5: make_tariff(5, "3 месяца"),
            }
            return tariff_map.get(tid)

        mock_model_data.tariffs.get_data.side_effect = mock_get_data
        getter = KeyStatsGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)

        assert result["stats"]["expiring_24h_paid"] == 2
        assert result["stats"]["expiring_24h_paid_by_tariff"] == {
            "1 месяц": 1,
            "3 месяца": 1,
        }

    @pytest.mark.asyncio
    async def test_24h_trial_with_tariff_name(self, mock_model_data, mock_dialog_manager):
        """24h trial ключи должны группироваться по названию тарифа."""
        keys = [
            make_key("t1@test.com", 1, 5 * 3600 * 1000, tariff_id=10),
        ]
        mock_model_data.keys.get_all.return_value = keys
        mock_model_data.tariffs.get_data.return_value = make_tariff(10, "Trial")

        getter = KeyStatsGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)

        assert result["stats"]["expiring_24h_trial"] == 1
        assert result["stats"]["expiring_24h_trial_by_tariff"] == {"Trial": 1}


# ============================================================================
# Тесты уведомлений
# ============================================================================


class TestKeyStatsGetterNotifications:
    """Тесты разбивки по статусу уведомлений."""

    @pytest.mark.asyncio
    async def test_notified_10h_breakdown(self, mock_model_data, mock_dialog_manager):
        """Статистика по notified_10h должна быть корректной (только 24h)."""
        keys = [
            make_key("n10h_true1@test.com", 1, 5 * 3600 * 1000, notified_10h=True),
            make_key("n10h_true2@test.com", 2, 6 * 3600 * 1000, notified_10h=True),
            make_key("n10h_false@test.com", 3, 7 * 3600 * 1000, notified_10h=False),
        ]
        mock_model_data.keys.get_all.return_value = keys
        getter = KeyStatsGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)

        assert result["stats"]["notified_10h_true"] == 2
        assert result["stats"]["notified_10h_false"] == 1

    @pytest.mark.asyncio
    async def test_notified_24h_breakdown(self, mock_model_data, mock_dialog_manager):
        """Статистика по notified_24h должна быть корректной (только 24h)."""
        keys = [
            make_key("n24h_true@test.com", 1, 5 * 3600 * 1000, notified_24h=True),
            make_key("n24h_false1@test.com", 2, 6 * 3600 * 1000, notified_24h=False),
            make_key("n24h_false2@test.com", 3, 7 * 3600 * 1000, notified_24h=False),
        ]
        mock_model_data.keys.get_all.return_value = keys
        getter = KeyStatsGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)

        assert result["stats"]["notified_24h_true"] == 1
        assert result["stats"]["notified_24h_false"] == 2


# ============================================================================
# Тесты комплексных сценариев
# ============================================================================


class TestKeyStatsGetterComplex:
    """Комплексные тесты."""

    @pytest.mark.asyncio
    async def test_mixed_scenario(self, mock_model_data, mock_dialog_manager):
        """Тест смешанной выборки: общие + 24h + уведомления."""
        keys = [
            # Trial, истекает через 5h, оба уведомления
            make_key("trial_24h@test.com", 1, 5 * 3600 * 1000, tariff_id=10,
                     notified_10h=True, notified_24h=True),
            # Paid, истекает через 10h
            make_key("paid_24h@test.com", 2, 10 * 3600 * 1000, tariff_id=5,
                     notified_10h=True, notified_24h=False, used_traffic=2000),
            # Paid, не истекает, неиспользуемый
            make_key("paid_unused@test.com", 3, 72 * 3600 * 1000, tariff_id=3,
                     used_traffic=0),
            # Уже истёк
            make_key("expired@test.com", 4, -1000, tariff_id=10),
        ]
        mock_model_data.keys.get_all.return_value = keys

        async def mock_get_data(tid):
            tariff_map = {
                10: make_tariff(10, "Trial"),
                5: make_tariff(5, "3 месяца"),
                3: make_tariff(3, "2 недели"),
            }
            return tariff_map.get(tid)

        mock_model_data.tariffs.get_data.side_effect = mock_get_data
        getter = KeyStatsGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)

        stats = result["stats"]
        # Общие
        assert stats["all_total"] == 4
        assert stats["all_trial"] == 2  # trial_24h + expired
        assert stats["all_paid"] == 2  # paid_24h + paid_unused
        assert stats["all_unused"] == 1  # paid_unused

        # 24h
        assert stats["expiring_24h_total"] == 2
        assert stats["expiring_24h_trial"] == 1
        assert stats["expiring_24h_paid"] == 1

        # Уведомления
        assert stats["notified_10h_true"] == 2
        assert stats["notified_24h_true"] == 1

    @pytest.mark.asyncio
    async def test_message_format(self, mock_model_data, mock_dialog_manager):
        """Сообщение должно содержать все разделы."""
        keys = [
            make_key("t1@test.com", 1, 5 * 3600 * 1000, tariff_id=10, used_traffic=0),
            make_key("p1@test.com", 2, 6 * 3600 * 1000, tariff_id=2, used_traffic=5000),
            make_key("u1@test.com", 3, 72 * 3600 * 1000, tariff_id=3, used_traffic=0),
        ]
        mock_model_data.keys.get_all.return_value = keys

        async def mock_get_data(tid):
            tariff_map = {
                10: make_tariff(10, "Trial"),
                2: make_tariff(2, "1 месяц"),
                3: make_tariff(3, "2 недели"),
            }
            return tariff_map.get(tid)

        mock_model_data.tariffs.get_data.side_effect = mock_get_data
        getter = KeyStatsGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)

        msg = result["STATS_MSG"]
        assert "Все ключи" in msg
        assert "Истекают 24h" in msg
        assert "Уведомления 24h" in msg
        # Все ключи: неиспользуемые — только число, без детализации
        assert "Неиспользуемые: 2" in msg
        # 24h: детализация по тарифам сохраняется
        assert "1 месяц" in msg
        assert "• Trial: 1" in msg


# ============================================================================
# Тесты обработки ошибок
# ============================================================================


class TestKeyStatsGetterErrors:
    """Тесты обработки ошибок."""

    @pytest.mark.asyncio
    async def test_exception_returns_error_message(self, mock_model_data, mock_dialog_manager):
        """При ошибке getter должен вернуть сообщение об ошибке."""
        mock_model_data.keys.get_all.side_effect = Exception("DB error")
        getter = KeyStatsGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)

        assert "STATS_MSG" in result
        assert "Ошибка" in result["STATS_MSG"]

    @pytest.mark.asyncio
    async def test_non_list_keys_wrapped(self, mock_model_data, mock_dialog_manager):
        """get_all() возвращает один ключ — должен быть обёрнут в список."""
        single_key = make_key("single@test.com", 1, 5 * 3600 * 1000)
        mock_model_data.keys.get_all.return_value = single_key
        getter = KeyStatsGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)

        assert result["stats"]["all_total"] == 1

    @pytest.mark.asyncio
    async def test_none_keys_returns_empty(self, mock_model_data, mock_dialog_manager):
        """get_all() возвращает None — должен вернуть пустую статистику."""
        mock_model_data.keys.get_all.return_value = None
        getter = KeyStatsGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)

        assert result["stats"]["all_total"] == 0

    @pytest.mark.asyncio
    async def test_tariff_get_data_exception_handled(self, mock_model_data, mock_dialog_manager):
        """Ошибка при получении тарифа не должна ломать всю статистику."""
        keys = [
            make_key("error@test.com", 1, 5 * 3600 * 1000, tariff_id=5),
        ]
        mock_model_data.keys.get_all.return_value = keys
        mock_model_data.tariffs.get_data.side_effect = Exception("Tariff DB error")

        getter = KeyStatsGetter(mock_model_data)
        result = await getter.get_data(mock_dialog_manager)

        assert result["stats"]["all_paid"] == 1
        assert "ID:5" in result["stats"]["all_paid_by_tariff"]
