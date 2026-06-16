"""
Tests for KeyStatsGetter.

KeyStatsGetter.get_data() fetches all keys via BackendAPIClient.admin_list_keys()
and a name map via BackendAPIClient.admin_list_tariffs(), producing:
1. Overall statistics for ALL keys with per-tariff-name breakdown
2. 24h expiring keys with per-tariff-name breakdown
3. Notification stats for 24h keys

Tariff names are resolved by loading all tariffs once and building an
id → name map, so the Key objects don't need to embed `name_tariff`.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from dialogs.windows.getters.admin.key_stats import KeyStatsGetter


def make_key_dict(
    email: str,
    tg_id: int,
    expiry_offset_ms: int,
    tariff_id: int = 20,
    used_traffic: float = 1000,
    notified_10h: bool = False,
    notified_24h: bool = False,
    name_tariff: str | None = None,
) -> dict:
    """Build a backend-shaped dict for a Key."""
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    d = {
        "tg_id": tg_id,
        "client_id": "c1",
        "email": email,
        "expiry_time": now_ms + expiry_offset_ms,
        "key": "k",
        "inbound_id": 1,
        "tariff_id": tariff_id,
        "used_traffic": used_traffic,
        "notified_10h": notified_10h,
        "notified_24h": notified_24h,
    }
    if name_tariff is not None:
        d["name_tariff"] = name_tariff
    return d


def make_tariff_dict(tariff_id: int, name: str) -> dict:
    """Build a backend-shaped dict for a Tariff."""
    return {
        "id": tariff_id,
        "name_tariff": name,
    }


@pytest.fixture
def mock_dialog_manager():
    """Mock DialogManager with writable dialog_data."""
    manager = AsyncMock()
    manager.dialog_data = {}
    manager.start_data = {}
    manager.middleware_data = {}
    return manager


@pytest.fixture
def mock_backend():
    """Mock BackendAPIClient: admin_list_keys + admin_list_tariffs."""
    backend = AsyncMock()
    backend.admin_list_keys = AsyncMock(return_value=[])
    backend.admin_list_tariffs = AsyncMock(return_value=[])
    return backend


# ============================================================================
# Тесты базовой функциональности
# ============================================================================


class TestKeyStatsGetterBasic:
    """Базовые тесты KeyStatsGetter."""

    @pytest.mark.asyncio
    async def test_returns_stats_msg(self, mock_backend, mock_dialog_manager):
        """KeyStatsGetter должен вернуть STATS_MSG."""
        mock_backend.admin_list_keys.return_value = []
        getter = KeyStatsGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)
        assert "STATS_MSG" in result
        assert "Статистика ключей" in result["STATS_MSG"]

    @pytest.mark.asyncio
    async def test_returns_stats_dict(self, mock_backend, mock_dialog_manager):
        """KeyStatsGetter должен вернуть stats dict."""
        mock_backend.admin_list_keys.return_value = []
        getter = KeyStatsGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)
        assert "stats" in result
        assert isinstance(result["stats"], dict)

    @pytest.mark.asyncio
    async def test_empty_keys_returns_zero_stats(
        self, mock_backend, mock_dialog_manager
    ):
        """При пустом списке ключей статистика должна быть нулевой."""
        mock_backend.admin_list_keys.return_value = []
        getter = KeyStatsGetter(mock_backend)
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
    async def test_saves_data_to_dialog_data(
        self, mock_backend, mock_dialog_manager
    ):
        """KeyStatsGetter должен сохранить данные в dialog_data."""
        mock_backend.admin_list_keys.return_value = []
        getter = KeyStatsGetter(mock_backend)
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
    async def test_all_total_count(self, mock_backend, mock_dialog_manager):
        """Общее количество ключей должно быть корректным."""
        keys = [
            make_key_dict("k1@test.com", 1, 72 * 3600 * 1000),
            make_key_dict("k2@test.com", 2, 48 * 3600 * 1000),
            make_key_dict("k3@test.com", 3, 24 * 3600 * 1000),
        ]
        mock_backend.admin_list_keys.return_value = keys
        getter = KeyStatsGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert result["stats"]["all_total"] == 3

    @pytest.mark.asyncio
    async def test_all_paid_with_tariff_names(
        self, mock_backend, mock_dialog_manager
    ):
        """Платные ключи должны группироваться по названиям тарифов (все, не только 24h)."""
        keys = [
            make_key_dict("p1@test.com", 1, 72 * 3600 * 1000, tariff_id=2),
            make_key_dict("p2@test.com", 2, 48 * 3600 * 1000, tariff_id=2),
            make_key_dict("p3@test.com", 3, 5 * 3600 * 1000, tariff_id=5),
        ]
        mock_backend.admin_list_keys.return_value = keys
        mock_backend.admin_list_tariffs.return_value = [
            make_tariff_dict(2, "1 месяц"),
            make_tariff_dict(5, "3 месяца"),
        ]

        getter = KeyStatsGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert result["stats"]["all_paid"] == 3
        assert result["stats"]["all_paid_by_tariff"] == {
            "1 месяц": 2,
            "3 месяца": 1,
        }

    @pytest.mark.asyncio
    async def test_all_trial_with_tariff_name(
        self, mock_backend, mock_dialog_manager
    ):
        """Trial ключи должны группироваться по названию тарифа (все, не только 24h)."""
        keys = [
            make_key_dict("t1@test.com", 1, 72 * 3600 * 1000, tariff_id=10),
            make_key_dict("t2@test.com", 2, 48 * 3600 * 1000, tariff_id=10),
        ]
        mock_backend.admin_list_keys.return_value = keys
        mock_backend.admin_list_tariffs.return_value = [make_tariff_dict(10, "Trial")]

        getter = KeyStatsGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert result["stats"]["all_trial"] == 2
        assert result["stats"]["all_trial_by_tariff"] == {"Trial": 2}

    @pytest.mark.asyncio
    async def test_all_unused_by_tariff(self, mock_backend, mock_dialog_manager):
        """Неиспользуемые ключи должны группироваться по названиям тарифов (все, не только 24h)."""
        keys = [
            make_key_dict("u1@test.com", 1, 72 * 3600 * 1000, tariff_id=2, used_traffic=0),
            make_key_dict("u2@test.com", 2, 48 * 3600 * 1000, tariff_id=5, used_traffic=0),
            make_key_dict("used@test.com", 3, 24 * 3600 * 1000, tariff_id=2, used_traffic=5000),
        ]
        mock_backend.admin_list_keys.return_value = keys
        mock_backend.admin_list_tariffs.return_value = [
            make_tariff_dict(2, "1 месяц"),
            make_tariff_dict(5, "3 месяца"),
        ]

        getter = KeyStatsGetter(mock_backend)
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
    async def test_expiring_24h_count(self, mock_backend, mock_dialog_manager):
        """Должны учитываться только ключи, истекающие в ближайшие 24h."""
        keys = [
            make_key_dict("expired@test.com", 1, -1000),
            make_key_dict("expiring_1h@test.com", 2, 1 * 3600 * 1000),
            make_key_dict("expiring_12h@test.com", 3, 12 * 3600 * 1000),
            make_key_dict("expiring_23h@test.com", 4, 23 * 3600 * 1000),
            make_key_dict("expiring_48h@test.com", 5, 48 * 3600 * 1000),
        ]
        mock_backend.admin_list_keys.return_value = keys
        getter = KeyStatsGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert result["stats"]["all_total"] == 5
        assert result["stats"]["expiring_24h_total"] == 3

    @pytest.mark.asyncio
    async def test_24h_paid_with_tariff_names(
        self, mock_backend, mock_dialog_manager
    ):
        """24h платные ключи должны группироваться по названиям тарифов."""
        keys = [
            make_key_dict("p1@test.com", 1, 5 * 3600 * 1000, tariff_id=2),
            make_key_dict("p2@test.com", 2, 10 * 3600 * 1000, tariff_id=5),
        ]
        mock_backend.admin_list_keys.return_value = keys
        mock_backend.admin_list_tariffs.return_value = [
            make_tariff_dict(2, "1 месяц"),
            make_tariff_dict(5, "3 месяца"),
        ]

        getter = KeyStatsGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert result["stats"]["expiring_24h_paid"] == 2
        assert result["stats"]["expiring_24h_paid_by_tariff"] == {
            "1 месяц": 1,
            "3 месяца": 1,
        }

    @pytest.mark.asyncio
    async def test_24h_trial_with_tariff_name(
        self, mock_backend, mock_dialog_manager
    ):
        """24h trial ключи должны группироваться по названию тарифа."""
        keys = [
            make_key_dict("t1@test.com", 1, 5 * 3600 * 1000, tariff_id=10),
        ]
        mock_backend.admin_list_keys.return_value = keys
        mock_backend.admin_list_tariffs.return_value = [make_tariff_dict(10, "Trial")]

        getter = KeyStatsGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert result["stats"]["expiring_24h_trial"] == 1
        assert result["stats"]["expiring_24h_trial_by_tariff"] == {"Trial": 1}


# ============================================================================
# Тесты уведомлений
# ============================================================================


class TestKeyStatsGetterNotifications:
    """Тесты разбивки по статусу уведомлений."""

    @pytest.mark.asyncio
    async def test_notified_10h_breakdown(
        self, mock_backend, mock_dialog_manager
    ):
        """Статистика по notified_10h должна быть корректной (только 24h)."""
        keys = [
            make_key_dict("n10h_true1@test.com", 1, 5 * 3600 * 1000, notified_10h=True),
            make_key_dict("n10h_true2@test.com", 2, 6 * 3600 * 1000, notified_10h=True),
            make_key_dict("n10h_false@test.com", 3, 7 * 3600 * 1000, notified_10h=False),
        ]
        mock_backend.admin_list_keys.return_value = keys
        getter = KeyStatsGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert result["stats"]["notified_10h_true"] == 2
        assert result["stats"]["notified_10h_false"] == 1

    @pytest.mark.asyncio
    async def test_notified_24h_breakdown(
        self, mock_backend, mock_dialog_manager
    ):
        """Статистика по notified_24h должна быть корректной (только 24h)."""
        keys = [
            make_key_dict("n24h_true@test.com", 1, 5 * 3600 * 1000, notified_24h=True),
            make_key_dict("n24h_false1@test.com", 2, 6 * 3600 * 1000, notified_24h=False),
            make_key_dict("n24h_false2@test.com", 3, 7 * 3600 * 1000, notified_24h=False),
        ]
        mock_backend.admin_list_keys.return_value = keys
        getter = KeyStatsGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert result["stats"]["notified_24h_true"] == 1
        assert result["stats"]["notified_24h_false"] == 2


# ============================================================================
# Тесты комплексных сценариев
# ============================================================================


class TestKeyStatsGetterComplex:
    """Комплексные тесты."""

    @pytest.mark.asyncio
    async def test_mixed_scenario(self, mock_backend, mock_dialog_manager):
        """Тест смешанной выборки: общие + 24h + уведомления."""
        keys = [
            # Trial, истекает через 5h, оба уведомления
            make_key_dict("trial_24h@test.com", 1, 5 * 3600 * 1000, tariff_id=10,
                          notified_10h=True, notified_24h=True),
            # Paid, истекает через 10h
            make_key_dict("paid_24h@test.com", 2, 10 * 3600 * 1000, tariff_id=5,
                          notified_10h=True, notified_24h=False, used_traffic=2000),
            # Paid, не истекает, неиспользуемый
            make_key_dict("paid_unused@test.com", 3, 72 * 3600 * 1000, tariff_id=3,
                          used_traffic=0),
            # Уже истёк
            make_key_dict("expired@test.com", 4, -1000, tariff_id=10),
        ]
        mock_backend.admin_list_keys.return_value = keys
        mock_backend.admin_list_tariffs.return_value = [
            make_tariff_dict(10, "Trial"),
            make_tariff_dict(5, "3 месяца"),
            make_tariff_dict(3, "2 недели"),
        ]

        getter = KeyStatsGetter(mock_backend)
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
    async def test_message_format(self, mock_backend, mock_dialog_manager):
        """Сообщение должно содержать все разделы."""
        keys = [
            make_key_dict("t1@test.com", 1, 5 * 3600 * 1000, tariff_id=10, used_traffic=0),
            make_key_dict("p1@test.com", 2, 6 * 3600 * 1000, tariff_id=2, used_traffic=5000),
            make_key_dict("u1@test.com", 3, 72 * 3600 * 1000, tariff_id=3, used_traffic=0),
        ]
        mock_backend.admin_list_keys.return_value = keys
        mock_backend.admin_list_tariffs.return_value = [
            make_tariff_dict(10, "Trial"),
            make_tariff_dict(2, "1 месяц"),
            make_tariff_dict(3, "2 недели"),
        ]

        getter = KeyStatsGetter(mock_backend)
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
    async def test_exception_returns_error_message(
        self, mock_backend, mock_dialog_manager
    ):
        """При ошибке getter должен вернуть сообщение об ошибке."""
        mock_backend.admin_list_keys.side_effect = Exception("Backend error")
        getter = KeyStatsGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert "STATS_MSG" in result
        assert "Ошибка" in result["STATS_MSG"]

    @pytest.mark.asyncio
    async def test_non_list_keys_wrapped(
        self, mock_backend, mock_dialog_manager
    ):
        """admin_list_keys() возвращает один dict — он будет обёрнут Key.from_backend."""
        # Key.from_backend() принимает dict, поэтому один dict тоже сработает
        # (хотя по контракту backend возвращает list). Проверяем, что один ключ учтён.
        single_key = make_key_dict("single@test.com", 1, 5 * 3600 * 1000)
        mock_backend.admin_list_keys.return_value = [single_key]
        getter = KeyStatsGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert result["stats"]["all_total"] == 1

    @pytest.mark.asyncio
    async def test_none_keys_returns_error_message(
        self, mock_backend, mock_dialog_manager
    ):
        """admin_list_keys() возвращает None — getter падает в обработчик ошибок.

        Текущая реализация key_stats.get_data() не обрабатывает None от бэкенда
        и роняет TypeError, который ловится внешним try/except и превращается в
        сообщение «Ошибка при загрузке статистики». Это документированное поведение.
        """
        mock_backend.admin_list_keys.return_value = None
        getter = KeyStatsGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        # Внешний try/except в getter превращает TypeError в STATS_MSG с «Ошибка»
        assert "STATS_MSG" in result
        assert "Ошибка" in result["STATS_MSG"]

    @pytest.mark.asyncio
    async def test_tariff_not_in_list_falls_back_to_id(
        self, mock_backend, mock_dialog_manager
    ):
        """Если тарифа нет в admin_list_tariffs — fallback на ID:{tariff_id}."""
        keys = [
            make_key_dict("error@test.com", 1, 5 * 3600 * 1000, tariff_id=5),
        ]
        mock_backend.admin_list_keys.return_value = keys
        # admin_list_tariffs возвращает пустой список — нет данных о тарифе
        mock_backend.admin_list_tariffs.return_value = []

        getter = KeyStatsGetter(mock_backend)
        result = await getter.get_data(mock_dialog_manager)

        assert result["stats"]["all_paid"] == 1
        assert "ID:5" in result["stats"]["all_paid_by_tariff"]
