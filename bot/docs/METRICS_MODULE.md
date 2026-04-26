# Metrics Module (`services/metrics/`)

## 📖 Оглавление

1. [Обзор](#обзор)
2. [Архитектура](#архитектура)
3. [Структура модуля](#структура-модуля)
4. [Каталог метрик](#каталог-метрик)
5. [Точки интеграции](#точки-интеграции)
6. [Конфигурация](#конфигурация)
7. [Использование в коде](#использование-в-коде)
8. [Кастомные Collector'ы](#кастомные-collectorы)
9. [Grafana дашборды](#grafana-дашборды)
10. [Алерты](#алерты)
11. [Добавление новых метрик](#добавление-новых-метрик)
12. [Тестирование](#тестирование)

---

## Обзор

**Metrics Module** — система мониторинга на базе `prometheus-client`, предоставляющая ~30 метрик для Prometheus/Grafana.

**Зависимость:** `prometheus-client>=0.20.0` (чистый Python, zero dependencies)

**Основные возможности:**
- ✅ Business метрики (платежи, ключи, регистрации, уведомления)
- ✅ Infrastructure метрики (DB pool, кеш, XUI API, Telegram API)
- ✅ Performance метрики (handler latency, background tasks)
- ✅ HTTP endpoint `/metrics` для Prometheus scraping
- ✅ Кастомные Collector'ы (pull-модель для кеша и DB pool)
- ✅ Минимальное вмешательство в существующий код

**Точка входа:** `services/metrics/setup.py:init_metrics()` — вызывается в `main.py:on_startup()`

---

## Архитектура

### Диаграмма потока

```
┌─────────────────────────────────────────────────────────────┐
│ main.py: on_startup()                                       │
│   └─ init_metrics(pool, cache_storage, metrics_port)        │
│       ├─ Регистрация CacheMetricsCollector (pull-модель)    │
│       ├─ Регистрация DBPoolMetricsCollector (pull-модель)   │
│       └─ Запуск HTTP сервера /metrics на METRICS_PORT       │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Prometheus scrape → GET /metrics                            │
│   ├─ Собирает Counter/Gauge/Histogram из REGISTRY           │
│   ├─ Вызывает CacheMetricsCollector.collect()               │
│   │   └─ Читает CacheStorage._storage (размеры namespace)   │
│   ├─ Вызывает DBPoolMetricsCollector.collect()              │
│   │   └─ Читает asyncpg.Pool (size/idle/used)              │
│   └─ Возвращает text/plain в формате Prometheus             │
└─────────────────────────────────────────────────────────────┘
```

### Два подхода к сбору метрик

| Подход | Описание | Где используется |
|--------|----------|-----------------|
| **Push** (инструментирование) | Код вызывает `.inc()` / `.observe()` в точках интеграции | Counters, Histograms |
| **Pull** (Collector) | Prometheus запрашивает — Collector читает состояние | Cache размеры, DB pool |

---

## Структура модуля

```
services/metrics/
├── __init__.py               # Экспорт REGISTRY
├── registry.py               # Определение всех Counter/Gauge/Histogram
├── setup.py                  # Инициализация: Collector'ы + HTTP сервер
├── http_server.py            # GET /metrics endpoint (aiohttp)
└── collectors/
    ├── __init__.py
    ├── cache_collector.py    # Pull-модель для CacheStorage
    └── db_pool_collector.py  # Pull-модель для asyncpg.Pool

tests/services/metrics/
├── __init__.py
├── test_registry.py          # Тесты: определения метрик, лейблы, типы
├── test_collectors.py        # Тесты: CacheMetricsCollector, DBPoolMetricsCollector
└── test_http_server.py       # Тесты: /metrics endpoint, content-type
```

---

## Каталог метрик

### 📊 Business: Платежи

| Метрика | Тип | Лейблы | Описание |
|---------|-----|--------|----------|
| `vpn_payment_total` | Counter | `status`, `operation` | Количество обработанных платежей |
| `vpn_payment_amount_rub_total` | Counter | `operation` | Суммарная выручка в рублях |
| `vpn_payment_processing_duration_seconds` | Histogram | `operation` | Время обработки платежа (buckets: 0.1–30s) |
| `vpn_webhook_requests_total` | Counter | `event_type`, `status` | Входящие вебхуки YooKassa |

**Значения лейблов:**
- `status`: `succeeded`, `canceled`, `error`
- `operation`: `create_key`, `renew_key`, `unknown`
- `event_type`: `payment.succeeded`, `payment.canceled`, `untrusted_ip`, `error`

### 🔑 Business: Ключи

| Метрика | Тип | Лейблы | Описание |
|---------|-----|--------|----------|
| `vpn_key_created_total` | Counter | `type` | Созданные ключи (`trial` / `paid`) |
| `vpn_key_renewed_total` | Counter | — | Продлённые ключи |
| `vpn_key_deleted_total` | Counter | — | Удалённые ключи |
| `vpn_key_creation_errors_total` | Counter | `error_type` | Ошибки при создании ключей |
| `vpn_keys_by_segment` | Gauge | `segment` | Количество ключей по сегментам |

### 👤 Business: Регистрация

| Метрика | Тип | Лейблы | Описание |
|---------|-----|--------|----------|
| `vpn_user_registered_total` | Counter | `type` | Зарегистрированные пользователи (`gift`, `referral`, `direct`) |
| `vpn_users_total_count` | Gauge | — | Общее количество пользователей в кеше |

### 📬 Business: Уведомления

| Метрика | Тип | Лейблы | Описание |
|---------|-----|--------|----------|
| `vpn_notification_sent_total` | Counter | `funnel_id` | Отправленные уведомления по воронкам |
| `vpn_notification_blocked_total` | Counter | `funnel_id` | Блокировки (TelegramForbiddenError) |
| `vpn_notification_error_total` | Counter | `funnel_id` | Прочие ошибки отправки |
| `vpn_notification_cycle_duration_seconds` | Histogram | — | Длительность цикла уведомлений |
| `vpn_rate_limiter_tokens` | Gauge | — | Текущий остаток токенов rate limiter |

**Значения `funnel_id`:** `key_expiry_24h`, `key_expiry_10h`, `trial_reminder`, `cold_lead`, `referral_bonus`

### ⚡ Infrastructure: Handler Latency

| Метрика | Тип | Лейблы | Описание |
|---------|-----|--------|----------|
| `vpn_handler_duration_seconds` | Histogram | `handler`, `event_type`, `status` | Время выполнения aiogram handlers (buckets: 10ms–5s) |

**Значения лейблов:**
- `event_type`: `message`, `callback`
- `status`: `success`, `error`

### 🗄️ Infrastructure: База данных

| Метрика | Тип | Лейблы | Описание |
|---------|-----|--------|----------|
| `vpn_db_pool_size` | Gauge | — | Размер пула соединений |
| `vpn_db_pool_free` | Gauge | — | Свободные соединения |
| `vpn_db_pool_used` | Gauge | — | Используемые соединения |

> Собираются через `DBPoolMetricsCollector` (pull-модель) из `asyncpg.Pool`.

### 💾 Infrastructure: Кеш

| Метрика | Тип | Лейблы | Описание |
|---------|-----|--------|----------|
| `vpn_cache_items_count` | Gauge | `namespace` | Количество элементов в кеше |
| `vpn_cache_expired_evictions_total` | Counter | `namespace` | Удалённые просроченные элементы |

> `cache_items_count` собирается через `CacheMetricsCollector` (pull-модель).
> `cache_expired_evictions_total` инкрементируется в `CacheStorage._remove_expired()`.

**Значения `namespace`:** `users`, `keys`, `servers`, `tariffs`, `gift_links`, `inbounds`, `payments`, `stocks`

### 🌐 Infrastructure: XUI API

| Метрика | Тип | Лейблы | Описание |
|---------|-----|--------|----------|
| `vpn_xui_api_calls_total` | Counter | `method` | Вызовы XUI API |
| `vpn_xui_api_errors_total` | Counter | `method`, `error_type` | Ошибки XUI API |
| `vpn_xui_api_duration_seconds` | Histogram | `method` | Время вызовов (buckets: 0.1–10s) |
| `vpn_xui_api_retries_total` | Counter | `method` | Повторные попытки |

**Значения `method`:** `add_client`, `extend_client_key`, `delete_client`, `get_inbounds`, `get_traffic`

### 📱 Infrastructure: Telegram Bot API

| Метрика | Тип | Лейблы | Описание |
|---------|-----|--------|----------|
| `vpn_telegram_messages_sent_total` | Counter | `result` | Отправленные сообщения |
| `vpn_telegram_flood_control_total` | Counter | — | Срабатывания flood control |

**Значения `result`:** `sent`, `blocked`, `retry_after`, `error`

### ⏰ Background Tasks

| Метрика | Тип | Лейблы | Описание |
|---------|-----|--------|----------|
| `vpn_background_sync_last_run_timestamp` | Gauge | — | Timestamp последней синхронизации |
| `vpn_background_sync_duration_seconds` | Histogram | — | Длительность синхронизации |
| `vpn_background_sync_errors_total` | Counter | — | Ошибки синхронизации |
| `vpn_background_notification_last_run_timestamp` | Gauge | — | Timestamp последнего цикла уведомлений |

### ❌ Общие ошибки

| Метрика | Тип | Лейблы | Описание |
|---------|-----|--------|----------|
| `vpn_errors_total` | Counter | `layer`, `error_type` | Ошибки по слоям приложения |

**Значения `layer`:** `middleware`, `service`, `payment`, `xui`, `db`, `notification`

---

## Точки интеграции

### Карта инструментирования

| Файл | Метрики | Что измеряется |
|------|---------|---------------|
| `middlewares/logging_middleware.py` | `handler_duration` | Latency каждого aiogram handler |
| `payments/pyments_webhook.py` | `payment_total`, `payment_amount_rub_total`, `payment_processing_duration`, `webhook_requests_total` | Платежи и вебхуки |
| `services/notification/manager.py` | `notification_sent/blocked/error_total`, `notification_cycle_duration` | Экспорт `FunnelRunReport` |
| `services/notification/rate_limiter.py` | `telegram_messages_sent_total`, `telegram_flood_control_total`, `rate_limiter_tokens` | Telegram отправка |
| `services/cache/storage.py` | `cache_expired_evictions_total` | Очистка просроченных элементов |
| `client.py` | `xui_api_calls/errors/duration/retries_total` | Все XUI API методы |
| `services/core/keys/utils/create_key.py` | `key_created_total`, `key_creation_errors_total` | Создание ключей |
| `services/core/payment/renewal_service.py` | `key_renewed_total` | Продление ключей |
| `middlewares/registration_users.py` | `user_registered_total` | Регистрация пользователей |
| `tasks.py` | `background_sync_*`, `background_notification_last_run` | Фоновые задачи |

---

## Конфигурация

### Переменные окружения

| Переменная | Default | Описание |
|-----------|---------|----------|
| `METRICS_PORT` | `9090` | Порт HTTP сервера `/metrics` |

### Prometheus `scrape_config`

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'vpn-bot'
    scrape_interval: 15s
    static_configs:
      - targets: ['bot-host:9090']
```

### Docker Compose (пример)

```yaml
services:
  bot:
    build: .
    ports:
      - "9090:9090"  # Prometheus metrics
    environment:
      - METRICS_PORT=9090

  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9091:9090"

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
```

---

## Использование в коде

### Импорт метрик

```python
from services.metrics.registry import payment_total, handler_duration
```

### Counter — инкрементирование

```python
# Без лейблов
key_renewed_total.inc()

# С лейблами
payment_total.labels(status="succeeded", operation="create_key").inc()

# Инкрементирование на N
payment_amount_rub_total.labels(operation="create_key").inc(299.0)
```

### Gauge — установка значения

```python
# Установить абсолютное значение
users_total_count.set(1500)
rate_limiter_tokens.set(25.0)

# Установить текущий timestamp
background_sync_last_run.set_to_current_time()

# Инкремент/декремент
db_pool_used.inc()
db_pool_used.dec()
```

### Histogram — наблюдение значения

```python
import time

t0 = time.monotonic()
# ... выполнение операции ...
elapsed = time.monotonic() - t0

handler_duration.labels(
    handler="my_handler",
    event_type="message",
    status="success",
).observe(elapsed)  # в секундах!
```

### ⚠️ Важно: единицы измерения

- **Время всегда в секундах** (Prometheus convention)
- `LoggingMiddleware` замеряет в мс → делим на 1000 перед `.observe()`
- Buckets уже настроены в `registry.py`, менять не нужно

---

## Кастомные Collector'ы

### CacheMetricsCollector

**Файл:** `services/metrics/collectors/cache_collector.py`

Читает `CacheStorage._storage` при каждом scrape. Не инструментирует hot path.

```python
class CacheMetricsCollector:
    def __init__(self, storage: CacheStorage) -> None:
        self._storage = storage

    def collect(self):
        gauge = GaugeMetricFamily(
            "vpn_cache_items_count",
            "Количество элементов в кеше по namespace",
            labels=["namespace"],
        )
        for namespace, items in self._storage._storage.items():
            gauge.add_metric([namespace], len(items))
        yield gauge
```

### DBPoolMetricsCollector

**Файл:** `services/metrics/collectors/db_pool_collector.py`

Читает `asyncpg.Pool.get_size()` / `.get_idle_size()` при каждом scrape.

```python
class DBPoolMetricsCollector:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    def collect(self):
        size = self._pool.get_size()
        idle = self._pool.get_idle_size()
        # yields: vpn_db_pool_size, vpn_db_pool_free, vpn_db_pool_used
```

### Регистрация Collector'ов

Происходит в `services/metrics/setup.py:init_metrics()`:

```python
REGISTRY.register(CacheMetricsCollector(cache_storage))
REGISTRY.register(DBPoolMetricsCollector(pool))
```

> ⚠️ Кастомные Collector'ы **дублируют** Gauge-метрики из `registry.py` (`cache_items_count`, `db_pool_*`). Gauge'и в registry — для ручного использования. Collector'ы — для автоматического scraping. При scrape Prometheus получает данные из Collector'ов.

---

## Grafana дашборды

### Дашборд 1: Business Overview

**Row 1 — Платежи (24h):**
```promql
# Платежей сегодня
sum(increase(vpn_payment_total{status="succeeded"}[24h]))

# Выручка сегодня
sum(increase(vpn_payment_amount_rub_total[24h]))

# Платежи по часам (succeeded vs canceled)
sum by (status) (rate(vpn_payment_total[1h]))
```

**Row 2 — Ключи:**
```promql
# Активных ключей по сегментам
vpn_keys_by_segment

# Созданные ключи (trial vs paid)
sum by (type) (rate(vpn_key_created_total[1h]))
```

**Row 3 — Пользователи:**
```promql
# Общее количество
vpn_users_total_count

# Новые регистрации
sum by (type) (rate(vpn_user_registered_total[1h]))
```

### Дашборд 2: Notifications & Funnels

```promql
# Отправлено / заблокировано / ошибки (stacked)
sum by (funnel_id) (rate(vpn_notification_sent_total[1h]))
sum by (funnel_id) (rate(vpn_notification_blocked_total[1h]))

# Длительность цикла
histogram_quantile(0.95, vpn_notification_cycle_duration_seconds_bucket)

# Flood control events
rate(vpn_telegram_flood_control_total[5m])
```

### Дашборд 3: Infrastructure Health

```promql
# DB Pool
vpn_db_pool_size
vpn_db_pool_used
vpn_db_pool_free

# Cache
vpn_cache_items_count

# XUI API latency p95
histogram_quantile(0.95, rate(vpn_xui_api_duration_seconds_bucket[5m]))

# Handler latency p50/p95
histogram_quantile(0.50, rate(vpn_handler_duration_seconds_bucket[5m]))
histogram_quantile(0.95, rate(vpn_handler_duration_seconds_bucket[5m]))
```

### Дашборд 4: Background Tasks

```promql
# Время последней синхронизации (алерт > 4 часов)
time() - vpn_background_sync_last_run_timestamp

# Длительность синхронизации
histogram_quantile(0.95, vpn_background_sync_duration_seconds_bucket)

# Ошибки синхронизации за 24h
increase(vpn_background_sync_errors_total[24h])
```

---

## Алерты

### Критические

```yaml
# Платёж завис > 30 секунд
- alert: PaymentProcessingSlow
  expr: histogram_quantile(0.95, rate(vpn_payment_processing_duration_seconds_bucket[5m])) > 30
  for: 5m

# Синхронизация не запускалась > 4 часов
- alert: SyncCacheStale
  expr: time() - vpn_background_sync_last_run_timestamp > 14400
  for: 5m

# DB Pool переполнен (> 90%)
- alert: DBPoolExhausted
  expr: vpn_db_pool_used / vpn_db_pool_size > 0.9
  for: 2m
```

### Предупреждения

```yaml
# XUI API ошибки > 5/мин
- alert: XUIAPIErrors
  expr: rate(vpn_xui_api_errors_total[5m]) > 5
  for: 3m

# Цикл уведомлений > 5 минут
- alert: NotificationCycleSlow
  expr: histogram_quantile(0.95, vpn_notification_cycle_duration_seconds_bucket) > 300
  for: 5m

# Массовая блокировка бота
- alert: MassBlockEvents
  expr: rate(vpn_telegram_messages_sent_total{result="blocked"}[1h]) > 50
  for: 10m
```

---

## Добавление новых метрик

### Шаг 1: Определить метрику в `registry.py`

```python
# services/metrics/registry.py

my_new_counter = Counter(
    "vpn_my_new_counter",            # Имя (prefix vpn_)
    "Описание метрики на русском",   # Описание
    ["label1", "label2"],            # Лейблы (опционально)
    registry=REGISTRY,               # Обязательно!
)
```

### Шаг 2: Импортировать и использовать

```python
from services.metrics.registry import my_new_counter

# В нужном месте кода
my_new_counter.labels(label1="value1", label2="value2").inc()
```

### Шаг 3: Добавить тест

```python
# tests/services/metrics/test_registry.py

def test_my_new_counter_labels(self):
    my_new_counter.labels(label1="v1", label2="v2").inc()
```

### Правила именования

- **Prefix:** `vpn_` для всех метрик
- **Suffix:** `_total` для Counter, `_seconds` для Histogram с временем, `_count` для Gauge с количеством
- **Лейблы:** snake_case, короткие имена
- **Описание:** на русском языке

### Для pull-модели (Collector)

1. Создать класс в `services/metrics/collectors/`
2. Реализовать `collect()` → `yield GaugeMetricFamily/CounterMetricFamily`
3. Реализовать `describe()` → `return []`
4. Зарегистрировать в `services/metrics/setup.py:init_metrics()`

---

## Тестирование

### Запуск тестов

```bash
# Только тесты метрик
pytest tests/services/metrics/ -v

# С покрытием
pytest tests/services/metrics/ --cov=services/metrics --cov-report=term-missing
```

### Структура тестов

| Файл | Описание | Тестов |
|------|----------|--------|
| `test_registry.py` | Определения метрик, лейблы, типы | 11 |
| `test_collectors.py` | CacheMetricsCollector, DBPoolMetricsCollector | 6 |
| `test_http_server.py` | `/metrics` endpoint, маршруты, content-type | 3 |

**Всего:** 22 теста

### Пример теста Collector'а

```python
def test_collect_with_namespaces(self):
    storage = MagicMock()
    storage._storage = {
        "users": {"u1": MagicMock(), "u2": MagicMock()},
        "keys": {"k1": MagicMock()},
    }
    collector = CacheMetricsCollector(storage)
    metrics = list(collector.collect())

    values_by_ns = {s.labels["namespace"]: s.value for s in metrics[0].samples}
    assert values_by_ns["users"] == 2
    assert values_by_ns["keys"] == 1
```

### Пример теста HTTP endpoint

```python
async def test_metrics_endpoint_returns_200():
    app = web.Application()
    setup_metrics_routes(app)

    async with TestClient(TestServer(app)) as client:
        resp = await client.get("/metrics")
        assert resp.status == 200
        assert "text/plain" in resp.headers.get("Content-Type", "")
```

---

## Связанные модули

- [docs/LOGGING.md](LOGGING.md) — Система логирования (loguru)
- [docs/NOTIFICATION_MODULE.md](NOTIFICATION_MODULE.md) — Воронки уведомлений (FunnelRunReport)
- [docs/PAYMENTS_MODULE.md](PAYMENTS_MODULE.md) — Платежи (YooKassa webhook)
- [docs/services.md](services.md) — Обзор сервисного слоя
- [docs/modules.md](modules.md) — Архитектура приложения
