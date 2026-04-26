# 📝 Руководство по логированию в проекте

## 🎯 Обзор

Проект использует **loguru** для структурированного логирования с поддержкой:
- 📁 Автоматической ротации и сжатия логов
- 🔐 Автоматической маскировки чувствительных данных
- 🏗️ Структурированных данных (JSON-like в extra полях)
- ⏱️ Отслеживания времени выполнения функций
- 🎨 Цветного вывода в консоль
- 🔍 **Trace ID** для трассировки запросов между модулями
- 🚦 **Rate limiting** для защиты от спама логами
- 📄 **JSON-формат** для production
- 📊 **Интеграция с Loki/Prometheus** для мониторинга

**Точка входа:** `logger.py:StructuredLogger` и специализированные функции.

---

## 📊 Формат логов

### Текстовый формат (development)
```
2026-02-24 14:30:45 | INFO     | services.payment:process_payment:108 | Payment completed | {"payment_id": "yoo_123", "amount": 99.99, "trace_id": "a1b2c3d4", "service": "bot_3xui"}
```

**Компоненты:**
- `{time:YYYY-MM-DD HH:mm:ss}` — дата и время
- `{level: <8}` — уровень (INFO, ERROR, DEBUG и т.д.)
- `{name}:{function}:{line}` — модуль:функция:номер строки
- `{message}` — основное сообщение
- `{extra}` — дополнительные структурированные данные (включая `trace_id` и `service`)

### JSON-формат (production)
```json
{
  "text": "2026-02-24 14:30:45 | INFO | services.payment:process_payment:108 | Payment completed | {\"payment_id\": \"yoo_123\", \"amount\": 99.99, \"trace_id\": \"a1b2c3d4\", \"service\": \"bot_3xui\"}",
  "record": {
    "message": "Payment completed",
    "level": {
      "name": "INFO",
      "no": 20
    },
    "extra": {
      "payment_id": "yoo_123",
      "amount": 99.99,
      "trace_id": "a1b2c3d4",
      "service": "bot_3xui"
    },
    "time": {
      "repr": "2026-02-24 14:30:45.123456",
      "timestamp": 1708783845.123456
    }
  }
}
```

### Консольный формат (с цветами)
```
🟢 2026-02-24 14:30:45 | 🔴 INFO     | 🔵 services.payment:process_payment:108 | ⚪ Payment completed | 🟣 {"payment_id": "yoo_123", "amount": 99.99, "trace_id": "a1b2c3d4"}
```

- 🟢 Время — **зелено**
- 🔴 Уровень — цвет по уровню severity
- 🔵 Модуль:функция:строка — **циан**
- ⚪ Сообщение — цвет уровня
- 🟣 Extra — **магента**

---

## 📁 Структура хранения логов

| Путь | Уровень | Формат | Ротация | Retention | Назначение |
|------|---------|--------|---------|-----------|-----------|
| `logs/application.log` | INFO+ | text | 3 часа | 30 дней | Основной лог приложения |
| `logs/application.json.log` | INFO+ | JSON | 100 MB | 30 дней | Production лог (JSON) |
| `logs_error/errors.log` | ERROR+ | text | 1 день | 90 дней | Ошибки (текст) |
| `logs_error/errors.json.log` | ERROR+ | JSON | 100 MB | 90 дней | Ошибки (JSON) |
| `stderr` | DEBUG+ | text+color | — | — | Консольный вывод |

**Асинхронное логирование:** `enqueue=True` — логирование не блокирует выполнение кода.

**Переменные окружения:**
- `LOG_ENVIRONMENT` — окружение (`development`/`production`)
- `LOG_FORMAT` — формат логов (`text`/`json`)

---

## 💻 Использование в коде

### ✅ Базовое логирование

```python
from logger import logger

# INFO
logger.info("User created", user_id=123, username="john_doe")

# DEBUG
logger.debug("Cache hit", key="user_123", ttl_seconds=3600)

# WARNING
logger.warning("API rate limit approaching", remaining_requests=10)

# ERROR
logger.error("Database connection failed", error=str(e), retry_count=3)

# CRITICAL
logger.critical("System shutdown initiated", reason="memory_limit_exceeded")

# SUCCESS (кастомный уровень)
logger.success("Migration completed", tables_migrated=5, duration_ms=1234)
```

### 📋 Структурированные данные

```python
# ПРАВИЛЬНО: передавать структурированные данные в extra
logger.info(
    "Payment processed",
    user_id=456,
    payment_id="yoo_abc123",
    amount=99.99,
    tariff_id=5,
    months=3
)
# Лог: {"user_id": 456, "payment_id": "yoo_abc123", "amount": 99.99, "tariff_id": 5, "months": 3}

# НЕПРАВИЛЬНО: конкатенировать в сообщение
logger.info(f"Payment {payment_id} for user {user_id} processed")  # ❌ потеряется структура
```

### 🎯 Специализированные функции

#### 1. Платежные события
```python
from logger import log_payment_event

await log_payment_event(
    payment_id="yoo_abc123",
    status="completed",
    amount=99.99,
    user_id=456,
    tariff_id=5
)
# Лог: Payment event | {"payment_id": "yoo_abc123", "status": "completed", "amount": 99.99, "user_id": 456, "tariff_id": 5}
```

#### 2. События бота (aiogram)
```python
from logger import log_aiogram_event

@router.message.register(Command("start"))
async def start_handler(message: types.Message):
    await log_aiogram_event(
        handler_name="start_command",
        message=message,
        full_name=message.from_user.full_name,
        is_bot=message.from_user.is_bot
    )
    # Лог: Aiogram event: start_command | {"user_id": 123456, "chat_id": 789, "message_type": "text", "full_name": "John Doe", "is_bot": false}
```

#### 3. Запросы к БД
```python
from logger import log_database_query

async def get_user_by_id(user_id: int):
    query = "SELECT * FROM users WHERE tg_id = $1"
    await log_database_query(
        query=query,
        params=(user_id,),
        source="user_service",
        operation="select"
    )
    return await pool.fetchrow(query, user_id)
# Лог: Database query executed | {"query": "SELECT * FROM users WHERE tg_id = $1", "params_length": 1, "source": "user_service", "operation": "select"}
```

#### 4. Вызовы XUI API
```python
from logger import log_xui_api_call

async def fetch_inbound_data(inbound_id: int):
    await log_xui_api_call(
        method="GET",
        endpoint=f"/xui/api/inbounds/{inbound_id}",
        inbound_id=inbound_id
    )
    return await xui_session.get_inbound(inbound_id)
# Лог: XUI API call | {"api_method": "GET", "endpoint": "/xui/api/inbounds/5", "inbound_id": 5}
```

#### 5. Действия пользователей
```python
from logger import log_user_action

async def purchase_vpn_key(user_id: int, tariff_id: int, months: int):
    await log_user_action(
        user_id=user_id,
        action="purchased_key",
        tariff_id=tariff_id,
        months=months,
        amount=total_price
    )
# Лог: User action | {"user_id": 123, "action": "purchased_key", "tariff_id": 5, "months": 3, "amount": 99.99}
```

#### 6. Вебхук события
```python
from logger import log_webhook_event

async def handle_payment_webhook(payload: dict):
    await log_webhook_event(
        event_type="payment.success",
        payload=payload,  # автоматически маскируется
        source="yookassa",
        ip_address=request.remote_addr
    )
# Лог: Webhook event | {"event_type": "payment.success", "payload": {...}, "source": "yookassa", "ip_address": "192.168.1.1"}
```

#### 7. Системные события
```python
from logger import log_system_event

async def initialize_services():
    await log_system_event(
        event="service_initialization_started",
        services=["cache", "database", "xui_session"]
    )
    # ... инициализация ...
    await log_system_event(
        event="service_initialization_completed",
        duration_ms=1234,
        status="success"
    )
# Лог: System event | {"event": "service_initialization_completed", "duration_ms": 1234, "status": "success"}
```

---

## 🔍 Trace ID — трассировка запросов

Каждый лог автоматически содержит `trace_id` — уникальный идентификатор (8 символов) для трассировки запроса между модулями.

### Автоматическая генерация

```python
from logger import logger

# trace_id генерируется автоматически при первом логe
logger.info("Запрос начат", user_id=123)
# Лог: {"user_id": 123, "trace_id": "a1b2c3d4", "service": "bot_3xui"}

logger.info("Запрос завершён")
# Лог: {"trace_id": "a1b2c3d4", "service": "bot_3xui"}  # тот же trace_id
```

### Ручная установка (в middleware)

```python
# middlewares/logging_middleware.py
from logger import set_trace_id, reset_trace_id
import uuid

async def __call__(self, handler, event, data):
    # Генерируем trace_id для каждого события
    set_trace_id(str(uuid.uuid4())[:8])
    try:
        return await handler(event, data)
    finally:
        reset_trace_id()  # Сброс после обработки
```

### Поиск по trace_id в Loki

```logql
# Найти все логи с конкретным trace_id
{trace_id="a1b2c3d4"}

# Найти все ошибки с trace_id
{trace_id="a1b2c3d4", level="ERROR"}
```

---

## 🚦 Rate limiting — защита от спама

Используй асинхронные методы для логирования с rate limiting:

```python
from logger import logger

# Логировать не чаще 1 раза в 10 секунд
await logger.error_async(
    "База данных недоступна",
    _rate_limit_key="db_connection_error",
    _rate_limit_secs=10
)

# При частых ошибках:
# 1. Первый лог записывается сразу
# 2. Следующие логи в течение 10 секунд подавляются
# 3. Через 10 секунд снова записывается один лог
# 4. В лог добавляется suppressed_logs=N (количество подавленных)
```

**Пример лога с rate limiting:**
```
2026-02-24 14:30:45 | ERROR | database:connect:50 | База данных недоступна | 
{"error_type": "ConnectionError", "suppressed_logs": 15, "rate_limit_secs": 10, "trace_id": "a1b2c3d4"}
```

---

## 📄 JSON-формат для production

Для включения JSON-формата установи переменные окружения:

```bash
# .env
LOG_ENVIRONMENT=production
LOG_FORMAT=json
```

**Преимущества JSON:**
- ✅ Машиночитаемый формат
- ✅ Легко парсить для анализа
- ✅ Интеграция с Loki/ELK
- ✅ Структурированные поля без парсинга

**Файлы логов:**
- `logs/application.json.log` — INFO+ логи
- `logs_error/errors.json.log` — ERROR+ логи

---

## 📊 Интеграция с мониторингом

### Prometheus алерты

Проект включает 11 правил алертов (`alerts.yml`):

| Алерт | Условие | Severity |
|-------|---------|----------|
| HighErrorRate | >10 ошибок/мин | critical |
| CriticalErrorsDetected | >0 CRITICAL | critical |
| DatabaseErrors | >5 ошибок БД/мин | warning |
| XuiApiErrors | >10 ошибок XUI/мин | warning |
| PaymentErrors | >3 ошибки платежей/мин | critical |
| SlowDatabaseQueries | >5 медленных запросов/мин | warning |

### Health Check endpoints

```bash
# Быстрая проверка
GET /health
# Ответ: {"status": "healthy", "database": {"status": "ok", "latency_ms": 12.5}}

# Полная проверка
GET /health?full=true
# Ответ: {"status": "healthy", "components": {...}, "uptime_seconds": 3600}

# Готовность
GET /ready
# Ответ: {"ready": true}

# Живость
GET /live
# Ответ: {"alive": true}
```

### Grafana + Loki + Tempo

Запуск мониторинга:

```bash
docker-compose -f docker-compose.monitoring.yml up -d
```

**Компоненты:**
- **Prometheus** — метрики и алерты
- **Grafana** — дашборды (порт 3001)
- **Loki** — агрегация логов
- **Promtail** — сбор логов
- **Tempo** — распределённая трассировка
- **OpenTelemetry Collector** — приём телеметрии

### @log_execution_time — логирование времени выполнения

```python
from logger import log_execution_time

@log_execution_time
async def expensive_operation():
    await asyncio.sleep(2)
    return {"result": "done"}

# При вызове логирует:
# DEBUG | Функция выполнена | {"function_name": "expensive_operation", "module_name": "services.operations", "elapsed_ms": 2000.45}
```

**Работает для:**
- Асинхронных функций
- Синхронных функций
- Методов класса

### @with_context — добавление контекста к логам

```python
from logger import with_context

@with_context(user_id=123, operation="payment", request_id="abc-123")
async def process_payment():
    logger.info("Processing started")
    logger.info("Processing completed")
    # Оба лога автоматически включат контекст: user_id, operation, request_id

# Логи:
# INFO | Processing started | {"user_id": 123, "operation": "payment", "request_id": "abc-123"}
# INFO | Processing completed | {"user_id": 123, "operation": "payment", "request_id": "abc-123"}
```

---

## 🔐 Маскировка чувствительных данных

### Автоматическая маскировка

Следующие поля **автоматически заменяются** на `***REDACTED***`:

```
password, secret, credit_card, api_key, access_token, refresh_token,
shop_id, secret_key, BOT_TOKEN, ADMIN_PASSWORD, DATABASE_URL, YOOKASSA_SECRET_KEY
```

### Примеры

```python
# ✅ Безопасно: чувствительные данные маскируются автоматически
logger.info(
    "Login attempt",
    username="john_doe",
    password="secret123",           # ← станет ***REDACTED***
    api_key="sk_live_xyz",          # ← станет ***REDACTED***
    bot_token="123456:ABCDEF"       # ← станет ***REDACTED***
)

# Результат в логе:
# {"username": "john_doe", "password": "***REDACTED***", "api_key": "***REDACTED***", "bot_token": "***REDACTED***"}

# ✅ Безопасно: также маскируются в вебхуках
await log_webhook_event(
    event_type="auth.success",
    payload={"user_id": 123, "secret_key": "xyz", "refresh_token": "abc"}
)
# payload также будет с маскированными полями
```

---

## 📋 Best Practices

### ✅ DO: Правильное логирование

```python
# 1. Логируй начало и конец важных операций
logger.info("Starting database migration", migration_name="add_users_table")
try:
    await migration.run()
    logger.success("Database migration completed", duration_ms=1234)
except Exception as e:
    logger.error("Database migration failed", error=str(e), migration_name="add_users_table")
    raise

# 2. Используй структурированные данные
logger.info(
    "User registered",
    user_id=123,
    method="telegram",
    referral_code="abc123",
    trial_enabled=True
)

# 3. Логируй контекст в исключениях
try:
    await payment_service.process(payment_id)
except PaymentError as e:
    logger.error(
        "Payment processing failed",
        payment_id=payment_id,
        user_id=user_id,
        error_code=e.code,
        error_message=e.message
    )

# 4. Используй подходящие уровни
logger.debug("Cache key generated", key="user_123")
logger.info("User connected", user_id=123)
logger.warning("Slow query detected", query="SELECT...", duration_ms=5000)
logger.error("Connection lost", attempts=3)
logger.critical("Out of memory", available_gb=0.1)
```

### ❌ DON'T: Неправильное логирование

```python
# ❌ Конкатенация в сообщение — потеря структуры
logger.info(f"User {user_id} created with tariff {tariff_id}")  # плохо

# ❌ Логирование очень больших объектов
logger.info("Response received", response_data=huge_dict)  # может замедлить систему

# ❌ Без контекста ошибки
logger.error("Operation failed")  # откуда ошибка? какая операция?

# ❌ Смешивание разных типов данных без описания
logger.info("Process result", data=result)  # что такое data?

# ❌ Логирование сырых исключений без контекста
logger.error(str(e))  # потеря информации
```

---

## 🔍 Примеры из реального кода

### Пример 1: Создание ключа VPN

```python
# services/keys/create.py
async def create_vpn_key(self, user_id: int, tariff_id: int, months: int):
    logger.info(
        "Starting VPN key creation",
        user_id=user_id,
        tariff_id=tariff_id,
        months=months
    )

    try:
        # Логируем запрос к XUI
        await log_xui_api_call(
            method="POST",
            endpoint="/xui/api/inbounds",
            user_id=user_id
        )

        key = await self.xui_session.create_user(...)

        logger.success(
            "VPN key created successfully",
            user_id=user_id,
            key_email=key.email,
            expiry_date=key.expiry.isoformat()
        )
        return key

    except XUIError as e:
        logger.error(
            "Failed to create VPN key",
            user_id=user_id,
            tariff_id=tariff_id,
            error_code=e.code,
            error_message=str(e)
        )
        raise
```

### Пример 2: Обработка платежа

```python
# services/payment/processor.py
async def process_payment(self, payment_id: str, user_id: int, amount: float):
    logger.info(
        "Payment processing started",
        payment_id=payment_id,
        user_id=user_id,
        amount=amount
    )

    try:
        await log_payment_event(
            payment_id=payment_id,
            status="processing",
            amount=amount,
            user_id=user_id
        )

        result = await self.yookassa.check_payment(payment_id)

        await log_payment_event(
            payment_id=payment_id,
            status="completed",
            amount=amount,
            user_id=user_id,
            transaction_id=result.id
        )

        logger.success("Payment completed", payment_id=payment_id, user_id=user_id)
        return result

    except Exception as e:
        logger.error(
            "Payment processing failed",
            payment_id=payment_id,
            user_id=user_id,
            error=str(e)
        )
        raise
```

### Пример 3: Обработчик команды бота

```python
# handlers/start.py
@router.message.register(Command("start"))
async def start_handler(message: types.Message, state: FSMContext):
    await log_aiogram_event(
        handler_name="start_command",
        message=message,
        username=message.from_user.username,
        is_premium=message.from_user.is_premium
    )

    user_id = message.from_user.id

    try:
        user = await user_service.get_or_create(user_id)

        logger.info(
            "User processed in start handler",
            user_id=user_id,
            is_new=not user.created_at,
            has_subscription=bool(user.active_key)
        )

        await message.answer("Добро пожаловать! 👋")

    except Exception as e:
        logger.error(
            "Start handler failed",
            user_id=user_id,
            error=str(e)
        )
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")
```

---

## 🐌 Slow Query Logging

Автоматическое обнаружение медленных запросов к базе данных:

```python
from utils_bot.logging_utils import DatabaseLogger
import time

async def get_user_data(user_id: int):
    start = time.monotonic()
    query = "SELECT * FROM users WHERE tg_id = $1"
    result = await pool.fetchrow(query, user_id)
    end = time.monotonic()
    
    # Автоматически определит медленный запрос
    await DatabaseLogger.log_query_with_timing(
        query=query,
        start_time=start,
        end_time=end,
        params=(user_id,),
        operation="get_user"
    )
    return result
```

**Порог медленного запроса:** 1000 мс (настраивается в `DatabaseLogger.SLOW_QUERY_THRESHOLD_MS`)

**Примеры логов:**
- Нормальный запрос (DEBUG): `{"duration_ms": 45.2, "query": "SELECT..."}`
- Медленный запрос (WARNING): `{"duration_ms": 1523.7, "threshold_ms": 1000, "query": "SELECT..."}`

---

## 🐛 Troubleshooting

### Проблема: Логи не видны в консоли

**Решение:** Убедись, что `setup_logging()` вызвана перед использованием логгера:
```python
from logger import setup_logging

setup_logging()  # Вызови это в main.py:on_startup()
```

### Проблема: Слишком много логов DEBUG уровня

**Решение:** Отключи DEBUG для библиотек в `logger.py:setup_logging()`:
```python
library_loggers = {
    "aiohttp": "WARNING",
    "asyncio": "WARNING",  # Если слишком много логов
}
```

### Проблема: Логи не сохраняются в файл

**Решение:** Проверь, что директории существуют:
```bash
mkdir -p logs logs_error
chmod 755 logs logs_error
```

### Проблема: Чувствительные данные не маскируются

**Решение:** Убедись, что ключ находится в `SENSITIVE_KEYS`:
```python
SENSITIVE_KEYS = {
    'password', 'secret', 'api_key', 'my_custom_secret'  # добавь свой ключ
}
```

### Проблема: JSON-логи не записываются

**Решение:** Проверь переменные окружения:
```bash
echo $LOG_ENVIRONMENT  # должно быть "production"
echo $LOG_FORMAT  # должно быть "json"
```

### Проблема: Trace ID не добавляется в логи

**Решение:** Убедись, что используешь актуальную версию `logger.py`:
```python
# Проверка
from logger import get_common_fields
print(get_common_fields())  # {"trace_id": "...", "service": "bot_3xui"}
```

### Проблема: Rate limiting не работает

**Решение:** Используй асинхронные методы:
```python
# ПРАВИЛЬНО:
await logger.error_async("Ошибка", _rate_limit_key="key", _rate_limit_secs=10)

# НЕПРАВИЛЬНО:
logger.error("Ошибка")  # rate limiting не применяется
```

---

## 📚 Ссылки

- **Реализация:** `logger.py`
- **Утилиты:** `utils_bot/logging_utils.py`
- **Health check:** `services/healthcheck.py`
- **Примеры использования:** `services/`, `handlers/`, `middlewares/`
- **Конфигурация:** `logger.py:setup_logging()`, `logger.py:SENSITIVE_KEYS`
- **Мониторинг:** `docker-compose.monitoring.yml`, `alerts.yml`, `prometheus.yml`
- **Loki:** `loki-config.yml`, `promtail-config.yml`
- **Tempo:** `tempo-config.yml`
- **OpenTelemetry:** `otel-collector-config.yml`
- **Библиотека:** [loguru документация](https://loguru.readthedocs.io/)

---

## 📝 Чек-лист перед коммитом

При добавлении нового функционала проверь:

- [ ] Логирую начало операции? (`logger.info()`)
- [ ] Логирую успешное завершение? (`logger.success()`)
- [ ] Логирую ошибки с контекстом? (`logger.error()`)
- [ ] Использую структурированные данные, а не конкатенацию?
- [ ] Чувствительные данные не попадают в логи? (будут маскироваться автоматически)
- [ ] Использую подходящие уровни (debug/info/warning/error/critical)?
- [ ] Для платежей использую `log_payment_event()`?
- [ ] Для вебхуков использую `log_webhook_event()`?
- [ ] Добавляю контекст в логи (user_id, email, operation)?
- [ ] Для повторяющихся событий использую rate limiting? (`logger.error_async()`)
- [ ] Для запросов к БД использую `log_query_with_timing()`?
