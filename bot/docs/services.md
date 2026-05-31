# Документация по модулю services ⚠️ Частично удалён

> ⚠️ **ВАЖНО:** После рефакторинга (30 мая 2026) бот стал **чистым UI-слоем**. Вся бизнес-логика (платежи, синхронизация, уведомления, аналитика) переехала в `backend/`.
> Бот общается с backend исключительно через `BackendAPIClient` (`api/backend_client.py`).

Модуль `services` содержит UI-хелперы Telegram-бота для управления VPN-подписками: кэш, диалоги, сценарии, лёгкие сервисы форматирования.

## Структура модуля (актуальная)

```
services/
├── __init__.py
├── api              # HTTP-клиент для backend API (BackendAPIClient)
├── cache            # In-memory TTL cache
├── conteiner        # DI-контейнер (punq)
├── core             # UI-хелперы (keys, user, gift, tariff, price, referral, stock)
├── metrics          # Prometheus registry (Counter/Gauge/Histogram)
└── scenarios        # Оркестраторы бизнес-сценариев
```

**❌ Удалённые подмодули:**
- `services/analytics/` — удалён (аналитика в backend)
- `services/billing/` — удалён (тарифы и акции в backend)
- `services/notification/` — удалён (воронки в backend)
- `services/synchron/` — удалён (синхронизация в backend)

## Подмодули

### `api`

HTTP-клиент для взаимодействия с backend API.

| Файл | Класс | Описание |
|------|-------|-------------|
| `backend_client.py` | `BackendAPIClient` | Асинхронный httpx-клиент. Все бизнес-операции (ключи, платежи, пользователи) через backend API |
| `schemas.py` | DTO | Модели запросов/ответов для API |

### `core`

UI-хелперы и локальная бизнес-логика (без прямого доступа к БД и 3x-UI). Обеспечивает работу с данными пользователей, ключами, тарифами и подарочными ссылками через cache + backend API.

#### `data` ⚠️ Legacy

Слой доступа к данным, объединяющий работу с кэшем и базой данных.

- `base.py` — Базовый класс `BaseData[T]` для асинхронных CRUD-операций, объединяющий кэш и базу данных
- `service.py` — Фасад `ServiceDataModel`, объединяющий все экземпляры `BaseData` для различных типов моделей
- `protocols.py` — Протокол `DataProtocol[T]`, определяющий интерфейс доступа к данным

#### `user`

Сервисы, связанные с управлением пользователями (UI layer).

- `utils/trial.py` — `TrialService`: Устанавливает триальный период пользователю (через backend API)
- `utils/saturation.py` — `SaturationUser`: Агрегирует полный контекст пользователя из cache
- `utils/checked_admin.py` — `CheckedUser`: Проверка прав администратора
- `utils/auto_register.py` — `AutoRegistrationService`: Автоматическая регистрация через backend API

**❌ Удалены:** `utils/delete_data.py`, `utils/saver.py`, `utils/checked_block.py` — управление пользователями в backend.

#### `keys` (UI layer only)

Сервисы, связанные с отображением ключей VPN (без прямого доступа к 3x-UI).

- `service.py` — `KeyService`: Подготавливает данные ключа для UI
- `models/key_model.py` — `KeyModel`: Доменная модель ключа с вычисляемыми свойствами
- `view/key_view.py` — `KeyView`: Статические методы для отображения ответов
- `controllers/key_controller.py` — `KeyController`: MVC-контроллер

**❌ Удалены:** `utils/calculator.py`, `utils/create_key.py`, `utils/formtion.py`, `utils/renewal.py`, `utils/updating.py` — создание/продление ключей теперь в backend.

#### `payment` ❌ Удалён

Сервисы платежей (`PaymentProcessor`, `KeyCreationService`, `KeyRenewalService`, `PaymentRouter`) удалены из бота.
Вся платёжная логика — в backend.

#### `gift`

Сервисы, связанные с подарочными ссылками.

- `gift_manager.py` — `GiftLinkProvider`: Управление жизненным циклом подарочных ссылок (создание, погашение)
- `repositories/gen_token.py` — `TokenGen`: Генератор уникальных токенов подарков
- `repositories/gen_url.py` — `GiftUrlGenerator`: Форматирование URL подарка
- `repositories/checker.py` — `CheckerGiftLink`: Проверка статуса подарочной ссылки

#### `segmentation`

Система сегментации пользователей для таргетированной коммуникации.

- `model.py` — `UserSegment` (Enum): Определение сегментов пользователей
- `base.py` — Базовые классы условий для сегментации
- `ruls.py` — Условия и правила сегментации пользователей
- `manager.py` — `SegmentationManager`: Пакетная сегментация пользователей

#### `tariff`

Сервисы, связанные с тарифами.

- `data.py` — `TariffData`: Получение тарифов из cache с фильтрацией для пользователей/администраторов

#### `price`

Сервисы ценообразования.

- `form_price.py` — `Pricing`: Формирование цены с учетом скидок и акций

#### `connect_module` ❌ Удалён

`FormConnectionData` удалён — данные для подключения теперь приходят из backend API.

#### `time_helper.py` ❌ Удалён

Утилиты для работы со временем в миллисекундах.

- `TimeHelper` — Кэшированные временные метки (текущее время, +24ч, +10ч и др.)
- `valid_24h_keys()` — Функция проверки, истекает ли ключ в течение 24 часов

### `notification`

Многоуровневая система уведомлений для пользователей.

- `core.py` — Базовые компоненты: типы воронок, стратегии, условные фильтры
- `manager.py` — `FunnelManager`: Управление и запуск воронок уведомлений
- `funnels/` — Конкретные воронки уведомлений:
  - `key_expiry.py` — Уведомления о заканчивающихся ключах
  - `trial_reminder.py` — Напоминания о триальной подписке
  - `referral_bonus.py` — Реферальные бонусы
  - `cold_lead_engagement.py` — Активация "холодных" лидов
- `utils/` — Вспомогательные утилиты для формирования сообщений и клавиатур

### `scenarios`

Оркестраторы бизнес-процессов.

- `factory_scenario.py` — `ScenarioFactory` (ABC): Абстрактный фабричный класс для сценариев
- `create_first_key_scenario.py` — `CreateFerstKeyScenario`: Создание первого пробного ключа для нового пользователя
- `gift_scenario.py` — `GiftActivationScenario`: Активация подарочных ссылок и создание связанных ключей

### `synchron`

Синхронизация данных с панелью управления XUI.

- `cache_comparator.py` — `CacheComparator`: Сравнение данных XUI и кэша
- `xui_fetcher.py` — `XUIFetcher`: Получение и валидация клиентов с панели XUI
- `key_creator.py` — `KeyCreator`: Создание объектов Key из клиентов XUI и сохранение в БД
- `traffic.py` — `TrafficUpdater`: Асинхронное обновление статистики трафика
- `database_synchronizer.py` — `DatabaseSynchronizer`: Основной оркестратор синхронизации

### `cache`

Система кэширования в памяти с TTL (временем жизни).

- `storage.py` — `CacheStorage`: Потокобезопасное хранилище с автоматическим истечением TTL
- `service.py` — `ModelCache[T]`, `CacheService`: Универсальный типизированный кэш
- `protocols.py` — `CacheProtocol[T]`: Интерфейс кэша
- `factory.py` — `LoaderFactory`: Фабрика для загрузки данных в кэш
- `loader.py` — `LoadingService`: Предварительная загрузка данных БД в кэш при запуске

### `conteiner`

Внедрение зависимостей через библиотеку `punq`.

- `app.py` — `get_container()`: Точка входа для контейнера зависимостей
- `protocol.py` — `ContainerProtocol`: Интерфейс регистратора сервисов
- `registrate/` — Регистраторы сервисов для DI-контейнера

### `billing`

Сервисы ценообразования и акций (частично реализованы).

- `stocs_service.py` — `StockManager`: Проверка активности акций и размера скидок
- `tariff_service.py` — `TariffManager`: Получение тарифов с применением скидок
- `referral_service.py` — `ReferralManager`: Заглушка для данных рефералов
- `payment_service.py` — Пустая заглушка

### `analytics`

Аналитика и бизнес-метрики для анализа эффективности сервиса.

**Воронки уведомлений:**
- `funnel_analytics.py` — `FunnelAnalytics`: Сбор статистики по воронкам уведомлений

**Метрики конверсии:**
- `conversions.py` — `ConversionMetricsService`: Метрики конверсии (регистрации, первые оплаты)

**Дашборды:**
- `dashboard_metrics.py` — `DashboardMetricsService`: Агрегация данных для дашбордов (пользователи, ключи, выручка)

**Lifetime Value:**
- `ltv_metrics.py` — `LtvMetricsService`: Расчёт пожизненной ценности пользователя

**Отток пользователей:**
- `churn_metrics.py` — `ChurnMetricsService`: Анализ и прогнозирование оттока

**Реферальная программа:**
- `referral_metrics.py` — `ReferralMetricsService`: Статистика реферальных начислений и эффективности

**Подарочные ссылки:**
- `gift_metrics.py` — `GiftMetricsService`: Анализ эффективности подарочных ссылок

**Финансовая аналитика:**
- `payment_metrics.py` — `PaymentMetricsService`: Статистика выручки и прогнозы
  - Выручка за год/месяц/неделю/день
  - Прогнозы на основе скользящего среднего и линейной регрессии
  - Комбинированный метод прогнозирования (60% moving_avg + 40% regression)
  - Расчёт уверенности прогноза и тренда роста

**Использование:**
```python
from services.analytics import PaymentMetricsService

# Инициализация
metrics = PaymentMetricsService(db_pool)

# Получение статистики
stats = await metrics.get_revenue_stats()
print(f"Выручка за месяц: {stats.month_total}")

# Прогноз
forecast = await metrics.forecast_revenue()
print(f"Прогноз на неделю: {forecast.week_forecast} ₽")
```

### `metrics`

Система мониторинга Prometheus. Подробная документация: [docs/METRICS_MODULE.md](METRICS_MODULE.md).

- `registry.py` — Определение ~30 Counter/Gauge/Histogram метрик
- `setup.py` — Инициализация Collector'ов и HTTP сервера `/metrics`
- `http_server.py` — Endpoint `/metrics` для Prometheus scraping
- `collectors/cache_collector.py` — Pull-модель для размеров кеша
- `collectors/db_pool_collector.py` — Pull-модель для asyncpg pool

## Зависимости

Модуль `services` зависит от следующих компонентов:

- `database` — Для доступа к репозиториям и моделям данных
- `models` — Для работы с dataclass моделями
- `cache` — Для кэширования данных
- `config` — Для доступа к конфигурации приложения
- `client` — Для взаимодействия с панелью 3x-ui
- `logger` — Для ведения логов

## Принципы проектирования

1. **Разделение ответственности** — Каждый сервис отвечает за конкретную бизнес-задачу
2. **Инъекция зависимостей** — Использование DI для упрощения тестирования и управления зависимостями
3. **Фасады и прокси** — `ServiceDataModel` и `BaseData` предоставляют унифицированный интерфейс к данным
4. **Кэширование** — Активное использование кэша для уменьшения нагрузки на БД
5. **Типизация** — Использование Generics и TypeVar для строгой типизации
6. **Обработка ошибок** — Централизованная обработка ошибок и логирование

## Пример использования

```python
from services.core.keys.controllers import KeyController
from services.core.data.service import ServiceDataModel

# Инициализация сервисов
data_service = ServiceDataModel(cache_service, data_service)
key_controller = KeyController(data_service)

# Получение данных ключа для диалога
key_data = await key_controller.getter_key_data(email)
```
