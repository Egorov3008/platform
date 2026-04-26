# Модуль синхронизации (services/synchron/)

Модуль отвечает за синхронизацию данных между **XUI-панелью**, **кешем** и **базой данных**. Запускается каждые 3 часа как фоновая задача и доступен для ручного запуска из админ-панели.

## Архитектура

```
┌──────────────────────────────────────────────────────────────┐
│              DatabaseSynchronizer (оркестратор)               │
│                      sync_data()                             │
└─────┬──────────┬───────────────┬───────────────┬─────────────┘
      │          │               │               │
      ▼          ▼               ▼               ▼
┌──────────┐ ┌──────────────┐ ┌───────────┐ ┌──────────────┐
│XUIFetcher│ │CacheComparator│ │KeyCreator │ │TrafficUpdater│
│          │ │              │ │           │ │              │
│Получение │ │Сравнение     │ │Создание   │ │Обновление    │
│клиентов  │ │панель↔кеш    │ │ключей/    │ │трафика       │
│с панели  │ │              │ │юзеров     │ │              │
└──────────┘ └──────────────┘ └─────┬─────┘ └──────────────┘
                                    │
                              ┌─────▼─────┐
                              │TariffMatch│
                              │er         │
                              │Определение│
                              │тарифа     │
                              └───────────┘
```

## Файлы модуля

| Файл | Строк | Назначение |
|------|-------|------------|
| `database_synchronizer.py` | 176 | Оркестратор, управляет потоком синхронизации |
| `xui_fetcher.py` | 86 | Извлечение и валидация клиентов с XUI-панели |
| `cache_comparator.py` | 107 | Сравнение данных панели и кеша (set difference) |
| `key_creator.py` | 104 | Создание ключей и пользователей в БД/кеше |
| `tariff_matcher.py` | 72 | Определение тарифа по параметрам клиента |
| `traffic.py` | 187 | Получение и обновление данных о трафике |

## Поток данных (sync_data)

### Фаза 1 — Получение данных с XUI-панели

`XUIFetcher.extract_clients(xui_session)`:
1. Загружает все inbound-ы с XUI-панели
2. Извлекает клиентов из каждого inbound
3. Валидирует: наличие `email` и `tg_id > 0`
4. Возвращает `List[Client]` с гарантированно валидными данными

```python
clients = await self.xui_fetcher.extract_clients(xui_session)
# → List[Client] (email, tg_id, limit_ip, total_gb, expiry_time, inbound_id)
```

### Фаза 2 — Сравнение с кешем

`CacheComparator` — двухфазный компаратор с внутренним состоянием:

```python
# 1. Загрузить данные панели (синхронно)
cache_comparator.set_panel_data(clients)

# 2. Загрузить данные кеша (асинхронно, из БД)
await cache_comparator.set_cache_data(
    get_all_keys_func=model_data.keys.get_all,
    get_all_users_func=model_data.users.get_all,
)

# 3. Вычислить разницу (set difference)
out_keys, out_users = cache_comparator.compare()
# out_keys  — email-ы, есть на панели, но нет в кеше
# out_users — tg_id, есть на панели, но нет в кеше
```

### Фаза 3 — Восстановление отсутствующих данных

`_restore_missing_data(clients, out_keys, out_users)`:
- Для каждого отсутствующего email из `out_keys`:
  - Если пользователь тоже отсутствует → `KeyCreator.ensure_user_exists(tg_id)`
  - Создаёт ключ → `KeyCreator.create_key(client)`
- `KeyCreator` сохраняет в БД и кеш через `ServiceDataModel`

### Фаза 4 — Обновление трафика

`_update_traffic_in_batches(clients, batch_size=50)`:
1. Загружает сервер (ID=2) из кеша
2. Обрабатывает клиентов пачками по `batch_size`
3. Для каждой пачки:
   - `TrafficUpdater.fetch_traffic_batch()` — параллельные HTTP-запросы к subscription endpoint (семафор: макс. 30 одновременных)
   - Для каждого клиента: `TrafficUpdater.update_key_with_traffic()` — обновление `Key` в БД
4. Пауза 0.1с между пачками

## Компоненты

### DatabaseSynchronizer

Главный оркестратор. Управляет жизненным циклом HTTP-сессии и координирует все фазы.

```python
synchronizer = DatabaseSynchronizer(
    xui_fetcher=XUIFetcher(),
    cache_comparator=CacheComparator(),
    key_creator=KeyCreator(model_data, pool, tariff_matcher),
    traffic_updater=TrafficUpdater(model_data),
    model_data=model_data,
    pool=pool,
)

# Использование как context manager (закрывает HTTP-сессию)
async with synchronizer:
    result = await synchronizer.sync_data(xui_session)
# result → {"total": 150, "successful": 148, "failed": 2}
```

**HTTP-сессия:** Ленивая инициализация `aiohttp.ClientSession` с лимитами:
- 100 соединений, 20 на хост, keepalive 30с
- Таймаут: 60с общий, 10с подключение, 30с чтение

### XUIFetcher

Stateless-сервис. Не хранит состояние, работает с переданной `XUISession`.

```python
fetcher = XUIFetcher()
inbounds = await fetcher.fetch_inbounds(xui_session)    # List[Inbound]
clients = await fetcher.extract_clients(xui_session)     # List[Client] (валидированные)
```

**Валидация клиентов:**
- Есть атрибут `email` и он непустой
- Есть атрибут `tg_id`, это `int`, и > 0

### CacheComparator

Stateful-компаратор. Хранит загруженные данные и результаты сравнения.

**Внутреннее состояние:**
```python
keys_panel: List[str]    # email-ы с панели
users_panel: List[int]   # tg_id с панели
keys_cache: List[str]    # email-ы из кеша
users_cache: List[int]   # tg_id из кеша
out_keys: List[str]      # отсутствующие ключи (панель - кеш)
out_users: List[int]     # отсутствующие юзеры (панель - кеш)
```

### KeyCreator

Создаёт пользователей и ключи в БД/кеше.

```python
creator = KeyCreator(model_data, pool, tariff_matcher)

# Создать юзера если не существует
await creator.ensure_user_exists(tg_id=123456)  # → bool

# Создать ключ из клиента XUI
key = await creator.create_key(client, used_traffic=0)  # → Optional[Key]
```

**Логика построения subscription-ссылки:**
- Если `client.email == client.sub_id`: `{subscription_url}/{email}`
- Иначе: `{subscription_url}/{sub_id}`

### TariffMatcher

Определяет тариф по параметрам клиента XUI. **4 уровня матчинга (fallback):**

| Уровень | Условие | Логика |
|---------|---------|--------|
| 1. Спец. inbound | `inbound_id` в `SPECIAL_INBOUND_TARIFF` и нет трафика | Хардкод: inbound_id=6 → tariff_id=1 |
| 2. Точный матч | `limit_ip` + `traffic_limit` совпадают | Сравнение с тарифами из кеша |
| 3. По limit_ip | Только `limit_ip` совпадает | Деградированный режим (WARNING) |
| 4. Дефолт | Ничего не совпало | `int(DEFAULT_PRICING_PLAN)` из конфига |

```python
matcher = TariffMatcher(model_data)
tariff_id = await matcher.match(client)  # → int
```

### TrafficUpdater

Асинхронное получение и обновление данных о трафике.

```python
updater = TrafficUpdater(model_data, semaphore=asyncio.Semaphore(30))

# Получить трафик для пачки клиентов (параллельно)
traffic_data = await updater.fetch_traffic_batch(clients, subscription_url, session)
# → Dict[email, Optional[Dict]]

# Парсинг заголовка Subscription-Userinfo
traffic_info = await updater.parse_traffic_info(response_data)
# → {"upload_bytes", "download_bytes", "total_bytes", "used_bytes",
#     "used_gb", "total_gb", "remaining_bytes", "usage_percent"}

# Обновить ключ в БД
success = await updater.update_key_with_traffic(pool, key, client, traffic_data)
```

**Парсинг трафика:** Разбирает заголовок `Subscription-Userinfo`:
```
upload=1000; download=2000; total=10000
```

**Обновляемые поля Key:**
- `used_traffic` — использованный трафик (байты)
- `total_gb` — общий лимит трафика (байты)
- `expiry_time` — время истечения (из XUI)
- `limit_ip` — лимит IP (из XUI)

## Точки вызова

### 1. Фоновая задача (каждые 3 часа)

```python
# tasks.py → BackgroundTaskManager.start_sync_cache()
while self.running:
    result = await synchronizer.sync_data(xui_session)
    self._cache_synced.set()  # сигнал для notification_bot
    await asyncio.sleep(3 * 3600)
```

**Важно:** `notification_bot` ожидает завершения первой синхронизации через `asyncio.Event` перед запуском цикла уведомлений — для точной сегментации пользователей.

### 2. Ручной запуск из админ-панели

```python
# getters/on_click/admin_click.py → click_sync_cache()
async with synchronizer:
    stats = await synchronizer.sync_data(xui_session)
# Результат отправляется админу в Telegram
```

## Обработка ошибок

Каждый компонент изолирует свои ошибки — сбой одного ключа не останавливает синхронизацию:

| Компонент | При ошибке | Поведение |
|-----------|------------|-----------|
| `XUIFetcher` | Ошибка API панели | Возвращает пустой список `[]` |
| `CacheComparator` | Ошибка загрузки кеша | Исключение пробрасывается выше |
| `KeyCreator` | Ошибка создания ключа | Возвращает `None`, лог ERROR |
| `TrafficUpdater` | Ошибка HTTP-запроса | Возвращает `None` для клиента, лог DEBUG |
| `DatabaseSynchronizer` | Критическая ошибка | Лог CRITICAL, возвращает `{"error": ...}` |

Фоновая задача в `tasks.py` при ошибке ждёт 5 минут и повторяет попытку.

## Тесты

**Расположение:** `tests/services/synchron/`

| Файл | Тестов | Что покрывает |
|------|--------|---------------|
| `test_database_synchronizer.py` | 13 | Полный цикл sync_data, восстановление данных, батч-обновление |
| `test_xui_fetcher.py` | 5 | Загрузка inbound-ов, валидация клиентов |
| `test_cache_comparator.py` | 4 | Загрузка данных, set difference |
| `test_key_creator.py` | 3-4 | Создание юзеров/ключей, обработка ошибок |
| `test_tariff_matcher.py` | 8 | Все 4 уровня матчинга |
| `test_traffic.py` | 8 | Fetch, парсинг, обновление ключей |
| **Итого** | **~33** | |

```bash
pytest tests/services/synchron/        # все тесты модуля
pytest tests/services/synchron/ -v     # с подробным выводом
```

## Зависимости

```
DatabaseSynchronizer
├── XUIFetcher              (без зависимостей)
├── CacheComparator         (без зависимостей)
├── KeyCreator
│   ├── ServiceDataModel    (кеш + БД)
│   ├── asyncpg.Pool
│   └── TariffMatcher
│       └── ServiceDataModel
├── TrafficUpdater
│   └── ServiceDataModel
├── ServiceDataModel
└── asyncpg.Pool
```

**Внешние зависимости:**
- `py3xui` — SDK для 3x-ui панели (Client, Inbound, AsyncApi)
- `aiohttp` — HTTP-клиент для запросов трафика
- `asyncpg` — PostgreSQL драйвер
