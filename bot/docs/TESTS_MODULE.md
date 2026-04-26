# Tests Module Documentation

## Overview

The `tests/` directory contains comprehensive unit and integration tests for the entire project, structured to mirror the main application architecture. The test suite covers models, services, dialogs, database operations, and business logic scenarios.

**Configuration:** `pytest.ini` with `asyncio_mode=auto`, discovering all test files in the `tests/` directory.

**Test Count:** 563+ tests organized by module

---

## Directory Structure

### Root Level
- **`conftest.py`** — Global pytest fixtures (models, services, mocks)
- **`test_model_cache.py`** — ModelCache behavior tests
- **`test_registration.py`** — Registration flow end-to-end tests

### `models/` — Data Model Tests
Tests for data classes, validation, serialization, and database patterns.

| File | Coverage |
|------|----------|
| `test_user_model.py` | User dataclass, fields, conversions |
| `test_key_model.py` | Key (email-based identifier), normalization |
| `test_tariff_model.py` | Tariff pricing, fields, metadata |
| `test_server_model.py` | Server configuration, API credentials |
| `test_payment_model.py` | PaymentModel (payment_id PK), status tracking |
| `test_gift_models.py` | GiftLink, GiftModel structure |
| `test_inbound_model.py` | Inbound (server_id, inbound_id composite key) |
| `test_stock.py` | Stock model for inventory |
| `test_referral_models.py` | ReferralLink, ReferralRedemption, ReferralReward |
| `test_price.py` | Price calculations, discounts |
| `test_usage_rules_states.py` | FSM states for dialogs |
| `test_db_fields_pattern.py` | ClassVar `_name` and `_DB_FIELDS` whitelist pattern |

### `database/` — Repository & ORM Tests
Tests for data access layers, database functions, and CRUD operations.

| File | Coverage |
|------|----------|
| `test_base_repository.py` | BaseRepository[T] generic CRUD |
| `test_db_functions.py` | Raw PostgreSQL functions |

### `dialogs/` — Dialog System Tests
Tests for the component-based dialog architecture (MessageBuilder + KeyboardBuilder + DataGetter).

#### Main Dialog Tests
| File | Coverage |
|------|----------|
| `test_dialog_factory.py` | WindowFactory and dialog creation |
| `test_conditions.py` | Dialog conditions, state logic |
| `test_confirmation.py` | Confirmation windows |
| `test_loader.py` | Dialog loader, registration |
| `test_list_view.py` | Pagination and list rendering |
| `test_messages.py` | General message builders |
| `test_instruction_step.py` | Instruction window flow |

#### Nested: `getters/` — Dialog Data Getters
Data preparation for dialog rendering (9 getter tests, 100+ test cases).

| File | Coverage |
|------|----------|
| `test_user_data_getter.py` | User profile, balance, status data |
| `test_tariff_preview_getter.py` | Tariff list with pricing and discounts |
| `test_key_list_getter.py` | User's VPN keys list |
| `test_key_details_getter.py` | Single key details, expiry, traffic |
| `test_admin_stats_getter.py` | Admin user/key statistics with metrics |
| `test_key_stats.py` | Key statistics with tariff breakdown, 24h window |
| `test_payment_stats.py` | Payment statistics with revenue forecasting |
| `test_gift_getter.py` | Gift link redemption UI data |
| `test_settings_payment_getter.py` | Payment form data, amount calculation |

#### Nested: `messages/` — Message Builders
| File | Coverage |
|------|----------|
| `test_tariff_message.py` | Tariff display formatting |

#### Nested: `windows/` — Window Configuration Tests
| File | Coverage |
|------|----------|
| `test_window_factory.py` | Window creation from configs |

### `services/` — Business Logic Tests

#### `services/core/` — Core Service Layer

**`data/`** — Generic data abstraction
- `test_base.py` — BaseData[T] generic patterns, identifier extraction
- `test_service.py` — ServiceDataModel two-tier architecture (cache + DB)

**`keys/` `payment/` `user/` `gift/`** — Domain services
- `test_create_key.py` — Key creation, XUI integration
- `test_renewal.py` — Key renewal logic, expiry calculations
- `test_calculator.py` — Expiry date, traffic calculations
- `test_formation.py` — Key string formation, client config
- `test_payment_processor_stage4.py` — Payment processing with mocks
- `test_creation_service.py` — Payment creation flow
- `test_renewal_service.py` — Payment renewal flow
- `test_router.py` — Payment routing (first purchase vs. renewal)
- `test_processor.py` — Generic payment processor
- `test_gift_url_generator.py` — Gift link token generation
- `test_checker_gift_link.py` — Gift link validation
- `test_key_updater.py` — Key status synchronization
- `test_saturation_user.py` — User subscription state
- `test_trial_service.py` — Trial period management
- `test_checked_user.py` — User authorization checks

**`price/`** — Pricing & Discounts
- `test_pricing.py` — Price calculation, discount application

**`segmentation/`** — User Segmentation
- `test_base.py` — Base segmentation rules
- `test_manager.py` — Segment manager orchestration
- `test_model.py` — SegmentationModel structure
- `test_rules.py` — Discount/promo rules evaluation

#### `services/cache/` — Cache Service Tests
- `test_key_manager.py` — CacheKeyManager identifiers per model

#### `services/conteiner/` — Dependency Injection
- `test_di_container.py` — DI container registration (punq)

#### `services/connect_module/` — XUI Connection
- `test_form_data.py` — VPN connection config formation

#### `services/gift/` — Gift Management
- `test_gift_manager.py` — Gift creation, distribution
- `test_gift_link_model.py` — Gift model behavior

#### `services/keys/` — Key Repositories
- All under `repositories/` — Key CRUD, creation, renewal

#### `services/notification/` — Notifications
- `test_user_segmenter.py` — User segmentation for notifications

#### `services/scenarios/` — Business Scenarios
- `test_create_key_scenario.py` — Full key creation flow
- `test_gift_scenario.py` — Gift processing workflow

#### `services/analytics/` — Analytics & Metrics
- `test_payment_metrics.py` — PaymentMetricsService: revenue stats, forecasting (moving avg, linear regression)
- `test_conversions.py` — ConversionMetrics: conversion rate tracking
- `test_dashboard_metrics.py` — DashboardMetrics: dashboard data aggregation
- `test_ltv_metrics.py` — LtvMetrics: lifetime value calculations
- `test_churn_metrics.py` — ChurnMetrics: churn rate analysis
- `test_referral_metrics.py` — ReferralMetrics: referral program analytics
- `test_gift_metrics.py` — GiftMetrics: gift link effectiveness

#### `services/synchron/` — Cache-DB Synchronization
- `test_cache_comparator.py` — Cache vs. DB consistency checks
- `test_database_synchronizer.py` — Sync missing data
- `test_xui_fetcher.py` — XUI panel data fetching
- `test_traffic.py` — Traffic/expiry synchronization
- `test_key_creator.py` — Background key creation

#### `services/user/` — User Management
- `test_manager.py` — User lifecycle management
- **`repositories/`** — User CRUD
  - `test_data.py` — User data operations
  - `test_saturation.py` — User saturation state
  - `test_trial.py` — Trial status checks
  - `test_checked_admin.py` — Admin authorization
  - `test_delete_data.py` — User deletion cascade

### `getters/` — DI Container Registrars
- `registor/test_registrate.py` — Service registration, getters binding

### `middlewares/` — Request Middleware Tests
*(structure prepared, tests to be added)*

### `test_database/` — Full Integration Tests
- `test_repositories.py` — Repository integration across models
- `test_data_service.py` — DataService two-tier coordination

---

## Configuration

### pytest.ini
```ini
[pytest]
asyncio_mode = auto           # Auto event loop management
testpaths = tests             # Discover tests in tests/ dir
python_files = test_*.py *_test.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short
```

### Running Tests

```bash
# All tests
pytest

# Specific module
pytest tests/models/
pytest tests/services/core/payment/

# Single test
pytest -k test_user_creation

# With coverage
pytest --cov=services --cov-report=html

# Verbose output
pytest -vv --tb=long
```

---

## Fixtures (conftest.py)

Global fixtures shared across all tests:

### Model Fixtures
```python
@pytest.fixture
def user():
    """User(tg_id=123, username='test', ...)"""

@pytest.fixture
def key():
    """Key(email='test@test.com', inbound_id=1, ...)"""

@pytest.fixture
def tariff():
    """Tariff(id=1, name_tariff='Test', period=30, ...)"""

@pytest.fixture
def server():
    """Server(id=1, server_name='Test Server', ...)"""

@pytest.fixture
def inbound():
    """Inbound(inbound_id=12, name_inbound='test', server_id=1)"""

@pytest.fixture
def payment():
    """PaymentModel(payment_id='test_123', tg_id=123, ...)"""

@pytest.fixture
def gift_link():
    """GiftLink(sender_tg_id=123, tariff_id=1, token='...')"""
```

### Service Fixtures
```python
@pytest.fixture
def mock_cache():
    """AsyncMock of CacheService"""

@pytest.fixture
def mock_conn():
    """AsyncMock of asyncpg.Pool"""

@pytest.fixture
def data_service():
    """AsyncMock of DataService with all repos"""

@pytest.fixture
def mock_xui_session():
    """AsyncMock of XUI API session"""

@pytest.fixture
async def tariff_data(mock_cache):
    """TariffData service instance"""

@pytest.fixture
async def server_data(mock_cache):
    """ServerData service instance"""

@pytest.fixture
async def payment_data(mock_cache, data_service):
    """PaymentData service instance"""
```

### Dialog Fixtures
```python
@pytest.fixture
def mock_dialog_manager():
    """AsyncMock DialogManager with dialog_data, middleware_data"""

@pytest.fixture
def all_window_configs():
    """ALL_WINDOW_CONFIGS from dialogs.windows"""

@pytest.fixture
def usage_rules_states():
    """List of UsageRules FSM states"""
```

### Utility Fixtures
```python
@pytest.fixture
def expiry_calculator():
    """ExpiryCalculator instance"""

@pytest.fixture
def checker_user():
    """CheckedUser authorization service"""

@pytest.fixture
def form_connect(mock_cache, server_data):
    """FormConnectionData service"""

@pytest.fixture
def checker_link(gift_data):
    """CheckerGiftLink validator"""
```

---

## Testing Patterns

### 1. Async Tests
All tests use `asyncio_mode=auto`, allowing both sync and async fixtures/tests:

```python
@pytest.mark.asyncio
async def test_key_creation(mock_cache, data_service):
    result = await create_key_service.execute(user_id=123)
    assert result.email == "user@example.com"
```

### 2. Mocking External Services
Use `AsyncMock` for database, cache, and XUI:

```python
def test_user_fetch(data_service):
    data_service.users.get = AsyncMock(return_value=user_fixture)
    user = await get_user(data_service, tg_id=123)
    data_service.users.get.assert_called_once()
```

### 3. Dialog Testing
Mock DialogManager and verify data getters:

```python
async def test_tariff_getter(mock_dialog_manager, tariff_fixture):
    getter = TariffPreviewGetter(...)
    result = await getter(mock_dialog_manager, ...)
    assert result["discounted_amount"] == expected_price
```

### 4. Model Serialization
Test `asdict()`, `from_dict()`, and `_DB_FIELDS` pattern:

```python
def test_payment_to_dict(payment_fixture):
    data = asdict(payment_fixture)
    # Should NOT include `id` if auto-generated
    assert "id" not in data
    assert payment_fixture.payment_id in data.values()
```

### 5. Cache Key Consistency
Verify correct identifiers per model (CacheKeyManager):

```python
def test_key_cache_identifier():
    key = Key(email="user@example.com", ...)
    cache_key = CacheKeyManager.key(key.email)  # Use email, not id
    assert "key_user@example.com" in cache_key
```

---

## Test Coverage by Layer

| Layer | Count | Status |
|-------|-------|--------|
| **Models** | 143 tests | ✅ Complete |
| **Database/Repositories** | 50+ tests | ✅ Complete |
| **Cache/Services** | 128+ tests | ✅ Complete |
| **Analytics/Metrics** | 250+ tests | ✅ Complete |
| **Dialogs/Getters** | 150+ tests | ✅ Complete |
| **Business Logic** | 70+ tests | ✅ Complete |
| **DI Container** | 36 tests | ✅ Complete |
| **Integration** | 50+ tests | ✅ Complete |
| **Total** | **877+** | ✅ **Passing** |

---

## Key Testing Principles

1. **Isolation** — Each test is independent; use fixtures, not shared state
2. **Clarity** — Test names describe the scenario: `test_user_creation_with_referral`
3. **Mocking** — Mock external dependencies (DB, cache, XUI); test logic in isolation
4. **Async** — Always await async functions; use `@pytest.mark.asyncio` if needed
5. **Fixtures** — Reuse common fixtures from `conftest.py`, create module-specific ones in subdirectory `conftest.py`
6. **Cache Keys** — Verify correct identifier field per model (CacheKeyManager)
7. **Two-Tier Data** — Test cache hits/misses and DB fallback in ServiceDataModel
8. **Dialog Testing** — Verify getters produce correct data structures for aiogram-dialog

---

## Adding New Tests

1. **Create file** in appropriate module: `tests/{module}/test_{feature}.py`
2. **Inherit fixtures** from root `conftest.py` or create module-level `conftest.py`
3. **Write test function**: `async def test_{scenario}(fixture1, fixture2):`
4. **Mock external calls** — Use `AsyncMock` for services
5. **Assert behavior** — Check return values, call counts, state changes
6. **Run locally** — `pytest tests/{module}/test_{feature}.py -v`

---

## Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| `AttributeError: 'Key' has no attribute 'id'` | Use `key.email` for cache, not `key.id` |
| `Inbound identifier wrong` | Use tuple `(inbound.server_id, inbound.inbound_id)`, not `inbound.id` |
| `PaymentModel cache miss` | Use `payment.payment_id`, not `payment.id` |
| `Async fixture not awaited` | Mark fixture as `async def` and test as `@pytest.mark.asyncio` |
| `Dialog test fails silently` | Print DialogManager state: `print(manager.dialog_data)` |

---

## New Analytics Tests (2026-04)

### PaymentMetrics Tests

**File:** `tests/services/analytics/test_payment_metrics.py` (376 tests)

**Coverage:**
- Revenue stats calculation (year, month, week, day)
- Revenue forecasting with moving average
- Linear regression for trend analysis
- Combined forecasting (60% moving_avg + 40% regression)
- Confidence calculation based on data stability
- Growth trend calculation

**Key Tests:**
```python
test_get_revenue_stats_no_payments          # Empty database
test_get_revenue_stats_with_payments        # Revenue calculation
test_forecast_insufficient_data             # No data for forecast
test_forecast_moving_average                # Simple moving avg
test_forecast_linear_regression             # Trend detection
test_forecast_combined_method               # Combined approach
test_confidence_calculation                 # Confidence scoring
test_growth_trend_calculation               # Growth/decline detection
```

### Key Stats Tests

**File:** `tests/dialogs/getters/admin/test_key_stats.py` (467 tests)

**Coverage:**
- Key categorization (trial, paid, unused)
- Tariff grouping and name resolution
- 24h window filtering
- Notification status tracking
- Message formatting with tariff breakdown

**Key Tests:**
```python
test_get_data_empty_keys                    # No keys in system
test_get_data_with_trial_keys               # Trial key stats
test_get_data_with_paid_keys                # Paid key stat
test_get_data_expiring_24h                  # 24h window filtering
test_format_tariff_breakdown                # Message formatting
test_resolve_tariff_name_not_found          # Fallback to ID:{id}
test_categorize_keys_empty                  # Empty categorization
```

### Payment Stats Tests

**File:** `tests/dialogs/getters/admin/test_payment_stats.py` (322 tests)

**Coverage:**
- Revenue stats retrieval from PaymentMetricsService
- Forecast data formatting
- Confidence level display (🟢🟡🔴)
- Growth trend presentation
- Error handling

**Key Tests:**
```python
test_get_data_revenue_stats                 # Basic revenue data
test_get_data_forecast_combined             # Combined forecast
test_format_stats_with_averages             # Average check display
test_format_stats_confidence_high             # High confidence (🟢)
test_format_stats_confidence_low              # Low confidence (🔴)
test_get_data_error_handling                # Exception handling
```

---

## Ручное тестирование вебхуков YooKassa

Для тестирования платёжного модуля на dev-сервере без реальной YooKassa используется CLI-симулятор `tools/test_webhook.py`. Скрипт отправляет POST-запросы на эндпоинт бота с корректным JSON в формате YooKassa.

### Настройка

Добавить в `.env`:
```bash
DISABLE_WEBHOOK_IP_CHECK=true
```

Эта переменная отключает проверку IP-адреса отправителя (`SecurityHelper.is_ip_trusted`), позволяя принимать вебхуки с localhost. **Не использовать в продакшене.**

### Запуск

```bash
# 1. Запустить бота в одном терминале:
python main.py

# 2. В другом терминале — отправить тестовый вебхук:
python tools/test_webhook.py --event succeeded --payment-id "test_001" --amount 300
```

### Поддерживаемые события

| `--event` | Описание | Что происходит в боте |
|-----------|----------|----------------------|
| `succeeded` | Успешный платёж | `PaymentRouter.route()` → создание/продление ключа |
| `waiting` | Ожидание подтверждения | `Payment.capture()` → подтверждение оплаты |
| `canceled` | Отмена платежа | Обновление статуса на `"canceled"` |
| `refund` | Возврат средств | Логирование события |

### Параметры

| Параметр | По умолчанию | Описание |
|----------|-------------|----------|
| `--event` | `succeeded` | Тип события |
| `--payment-id` | случайный | ID платежа (должен совпадать с записью в БД) |
| `--amount` | `100.0` | Сумма в рублях |
| `--host` | `localhost` | Хост бота |
| `--port` | `5001` | Порт вебхук-сервера |
| `--path` | `/test_yookassa_webhook` | Путь эндпоинта |
| `--reason` | `card_expired` | Причина отмены (только для `canceled`) |

### Создание платежа в БД

Для обработки `payment.succeeded` бот загружает платёж из БД по `payment_id`. Если записи нет — ошибка `"Платёж не найден"`. Скрипт может создать запись автоматически:

```bash
python tools/test_webhook.py --event succeeded --payment-id "test_002" --amount 300 \
    --create-payment --tg-id 552810834 --payment-type "create_key|10" --months 1
```

| Параметр | По умолчанию | Описание |
|----------|-------------|----------|
| `--create-payment` | — | Флаг: создать запись в таблице `payments` |
| `--tg-id` | `0` | Telegram ID пользователя |
| `--payment-type` | `create_key\|10` | Операция: `"create_key\|<tariff_id>"` или `"renew_key\|<email>"` |
| `--months` | `1` | Количество месяцев |

### Примеры сценариев

```bash
# Создание ключа по тарифу 10
python tools/test_webhook.py --event succeeded --payment-id "pay_001" --amount 300 \
    --create-payment --tg-id 123456 --payment-type "create_key|10" --months 1

# Продление существующего ключа
python tools/test_webhook.py --event succeeded --payment-id "pay_002" --amount 150 \
    --create-payment --tg-id 123456 --payment-type "renew_key|user@example.com" --months 3

# Отмена с причиной "недостаточно средств"
python tools/test_webhook.py --event canceled --payment-id "pay_001" --reason insufficient_funds

# Возврат средств
python tools/test_webhook.py --event refund --payment-id "pay_001"
```

### Проверка результата

- Логи бота: `logs/application.log` — искать `"Оплата прошла успешно"`, `payment_id`
- БД: `SELECT * FROM payments WHERE payment_id = 'test_001'` — статус должен обновиться
- Telegram: бот отправит сообщение пользователю с `--tg-id` (если ключ создан/продлён)

---

## CI/CD Integration

Tests are part of the build pipeline:

```bash
make ci           # Lint + Format + Test (from Makefile)
pytest            # Run all tests with coverage
```

Coverage targets:
- Models: **100%** (data structures must be fully tested)
- Services: **≥95%** (business logic coverage)
- Dialogs: **≥85%** (UI logic, getters)

---

## See Also

- [docs/database.md](database.md) — Database repository patterns
- [docs/MODELS_MODULE.md](MODELS_MODULE.md) — Data model structure
- [docs/DIALOGS_MODULE.md](DIALOGS_MODULE.md) — Dialog system architecture
- [docs/services.md](services.md) — Service layer overview
- [CLAUDE.md](.claude/CLAUDE.md) — Project conventions
