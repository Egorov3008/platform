# Документация по модулям — Bot_3xui_vpn

> ⚠️ **ВАЖНО:** После рефакторинга (30 мая 2026) бот стал **чистым UI-слоем**. Вся бизнес-логика (ключи, платежи, синхронизация, уведомления, аналитика) переехала в `backend/`. Бот общается с backend исключительно через `BackendAPIClient` (`api/backend_client.py`). Этот документ актуализирован для отражения новой архитектуры.

Telegram-бот (aiogram 3) для управления подписками на VPN. Обрабатывает пользовательский интерфейс: регистрацию, управление ключами, оплату, подарочные ссылки, реферальную систему, тарифы и административные функции. Вся бизнес-логика делегируется backend API.

---


## Содержание

- [Корневые модули](#root-modules)
- [api/](#api) — HTTP-клиент для backend API
- [database/](#database)
- [models/](#models)
- [services/core/](#servicescore)
- [services/cache/](#servicescache)
- [services/conteiner/](#servicesconteiner)
- [services/scenarios/](#servicesscenarios)
- [dialogs/](#dialogs)
- [getters/](#getters)
- [handlers/](#handlers)
- [middlewares/](#middlewares)
- [states/](#states)
- [registration/](#registration)
- [widgets/](#widgets)
- [utils_bot/](#utils_bot)
- [core/](#core)

---

## Корневые модули

### `main.py`

Точка входа. Организует запуск бота, регистрацию middleware и опрос.

| Функция | Описание |
|----------|-------------|
| `on_startup()` | Инициализирует DI-контейнер, кэш, запускает фоновые задачи (no-op) |
| `setup_middlewares()` | Регистрирует стек middleware: DI → Cache → Registration → AdminSearch → Subscription → Logging → DialogErrorHandler |
| `main()` | Основная асинхронная точка входа — настройка, graceful restart, опрос бота |

### `config.py`

Центральный загрузчик конфигурации из `.env`.

| Группа | Переменные |
|-------|-----------|
| Бот | `API_TOKEN`, `BOT_NAME`, `URL_BOT`, `DEFAULT_COMMANDS` |
| База данных | `DATABASE_URL`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` |
| Панель 3x-ui | `API_URL`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `LIMIT_IP` |
| YooKassa | `YOOKASSA_SHOP_ID`, `YOOKASSA_SECRET_KEY`, `YOOKASSA_ENABLE` |
| Webhook | `WEBHOOK_HOST`, `WEBHOOK_PORT`, `WEBHOOK_URL`, `WEBHOOK_PATH` |
| Тарифы | `AVAILABLE_RATES_LIST`, `RENEWAL_PRICES`, `AVAILABLE_CONNECTIONS` |
| Рефералы | `REFERRAL_BONUS_PERCENTAGES` (вложенный словарь: 10%, 5%, 2% для уровней 1-3) |
| Загрузки | Ссылки для клиентов Android, iOS, Windows, Linux |

### `client.py` ❌ Удалён

Клиент 3x-ui (`XUISession`, `py3xui.AsyncApi`) удалён из бота. Все операции с панелью теперь выполняются backend'ом через `backend/client.py` (native standalone API).

### `tasks.py`

Менеджер фоновых асинхронных задач (теперь **no-op stub**).

> **Все фоновые задачи** (синхронизация кэша, воронки уведомлений, webhook-сервер) переехали в `backend/background/scheduler.py`.

| Класс/Метод | Описание |
|--------------|-------------|
| `BackgroundTaskManager` | Организует фоновые операции (сейчас — пустая заглушка) |
| `start_all_tasks()` | Запускает задачи (логирует "none active") |
| `stop_all_tasks()` | Graceful shutdown, отменяет задачи |

### `logger.py`

Структурированная система логирования с бэкендом loguru.

| Класс/Функция | Описание |
|----------------|-------------|
| `StructuredLogger` | Основной фасад логгера (`debug`, `info`, `warning`, `error`, `critical`, `success`) |
| `InterceptHandler` | Перехватчик из стандартного Python → loguru |
| `setup_logging()` | Инициализирует файловое + консольное логирование с ротацией |
| `sanitize_data()` | Рекурсивно маскирует чувствительные ключи |
| `log_execution_time()` | Декоратор, логирующий длительность выполнения функции |
| Специализированные логгеры | `log_aiogram_event()`, `log_database_query()`, `log_xui_api_call()`, `log_payment_event()` и др. |

**Файлы логов:** `logs/application.log` (INFO, 14 дней), `logs_error/errors.log` (ERROR, 28 дней), ежедневная ротация с ZIP.

### `services/metrics/`

Реестр метрик Prometheus (инкрементируется в коде бота). Подробная документация: [docs/METRICS_MODULE.md](METRICS_MODULE.md).

> **HTTP-сервер `/metrics` и pull-модель collectors удалены.** Метрики инкрементируются в коде, но scraping endpoint теперь в backend (если нужен).

| Компонент | Описание |
|-----------|-------------|
| `registry.py` | Единый реестр всех Counter/Gauge/Histogram метрик |

**Категории метрик:** Business (регистрации), Telegram API, Dialog handlers.

### `bot_project.py`

Экземпляр бота Aiogram и настройка диспетчера.

| Компонент | Описание |
|-----------|-------------|
| `bot` | Экземпляр бота (режим парсинга HTML) |
| `storage` | MemoryStorage для FSM |
| `dp` | Диспетчер |
| `set_bot_commands()` | Регистрирует команду `/profile` |
| `error_handler()` | Глобальный обработчик ошибок с логированием трассировки |

---

## `database/` ⚠️ Legacy (backend only)

> Бот **больше не обращается к БД напрямую**. Слой `database/` (asyncpg, `BaseRepository`, `DataService`) остался в кодовой базе как legacy, но фактически используется только **backend'ом**. Бот получает все данные через `BackendAPIClient` (`api/backend_client.py`).

Слой абстракции базы данных с универсальным CRUD, паттерном репозитория и asyncpg.

### `base.py`

| Компонент | Описание |
|-----------|-------------|
| `create_db_pool() -> Pool` | Создаёт пул соединений asyncpg |
| `BaseRepository[T]` | Универсальный асинхронный репозиторий CRUD |

**Методы BaseRepository:**

| Метод | Сигнатура | Описание |
|--------|-----------|-------------|
| `get()` | `async get(pool, **kwargs) -> Optional[T]` | Получает одну запись по одному параметру фильтра |
| `get_all()` | `async get_all(pool) -> List[T]` | Получает все записи |
| `create()` | `async create(pool, **kwargs) -> bool` | Вставляет новую запись |
| `update()` | `async update(pool, search_data, **kwargs) -> bool` | Обновляет запись; исключает поля поиска из SET |
| `delete()` | `async delete(pool, **kwargs) -> bool` | Удаляет запись по фильтру |

### `service.py` — `DataService`

Фасад, объединяющий все экземпляры репозиториев:

| Атрибут | Модель | Таблица |
|-----------|-------|-------|
| `users` | `User` | `users` |
| `keys` | `Key` | `keys` |
| `servers` | `Server` | `servers` |
| `payments` | `PaymentModel` | `payments` |
| `tariffs` | `Tariff` | `tariff` |
| `inbounds` | `Inbound` | `inbound` |
| `gifts` | `GiftLink` | `gift_links` |
| `stocks` | `Stock` | `stocks` |

### `protocols.py` — `DatabaseProtocol[T]`

Универсальный протокол, определяющий контракт интерфейса базы данных: `get`, `get_all`, `create`, `update`, `delete`.

### `auth/`

| Файл | Класс | Описание |
|------|-------|-------------|
| `repositories.py` | `AuthRepository` | Управляет таблицей `registrate_msg_user`: проверка существования пользователя, получение статуса регистрации, обновление счётчика сообщений |
| `services.py` | `AuthService` | Слой сервиса, обёртывающий AuthRepository с логированием. Глобальный экземпляр: `auth_srv` |

---

## `models/`

Все модели — **dataclass** с сериализацией `to_dict()` / `from_dict()`.

### `users/user.py` — `User`

| Поле | Тип | Описание |
|-------|------|-------------|
| `tg_id` | `int` | ID пользователя Telegram |
| `username`, `first_name`, `last_name` | `Optional[str]` | Информация о пользователе |
| `is_admin` | `bool` | Флаг администратора |
| `trial` | `int` | Статус триала (0 = не использован, 1 = использован) |
| `server_id` | `Optional[int]` | Назначенный сервер |
| `referral_id` | `Optional[int]` | ID реферальной ссылки |
| `is_blocked` | `bool` | Флаг блокировки |
| `created_at`, `updated_at` | `datetime` | Метки времени |

### `keys/key.py` — `Key`

| Поле | Тип | Описание |
|-------|------|-------------|
| `tg_id` | `int` | ID владельца Telegram |
| `client_id` | `str` | ID клиента 3x-ui |
| `email` | `str` | Идентификатор электронной почты клиента |
| `expiry_time` | `int` | Метка времени окончания (мс) |
| `key` | `str` | Строка конфигурации подписки |
| `inbound_id` | `int` | ID входящего соединения сервера |
| `total_gb` | `Optional[int]` | Лимит данных (по умолчанию 10 ГБ) |
| `tariff_id`, `name_tariff` | `Optional` | Информация о тарифе |
| `used_traffic` | `Optional[float]` | Текущее использование |
| `notified_10h`, `notified_24h` | `bool` | Флаги уведомлений о окончании |

Свойство: `warp_expiry_time` — форматированное окончание `'ГГГГ-ММ-ДД ЧЧ:ММ'`.

### `servers/server.py` — `Server`

Поля: `id`, `cluster_name`, `server_name`, `api_url`, `subscription_url`, `login`, `password`.

### `servers/inbound.py` — `Inbound`

Поля: `server_id`, `inbound_id`, `name_inbound`.

### `tariffs/tariff.py` — `Tariff`

Поля: `id`, `name_tariff`, `amount` (цена), `description`, `limit_ip`, `period` (дней, по умолчанию 30), `traffic_limit` (ГБ).

### `gifts/gift_link.py` — `GiftLink`

Поля: `sender_tg_id`, `tariff_id`, `token`, `recipient_tg_id`, `email`, `_status` ("active"/"redeemed").

Методы: `is_redeemable()`, `redeem(recipient_tg_id, email)`, `is_expired(max_days=30)`.

### `payments/payment.py` — `PaymentModel`

Поля: `payment_id` (ID YooKassa), `tg_id`, `amount`, `payment_type`, `status` (по умолчанию "success"), `created_at`.

### `price_model/price.py` — `Price`

Поля: `amount`, `stock` (значение скидки), `type_stock` ("fix"/"percent"/"").

Свойство: `format_price` — рассчитывает итоговую цену после скидки.

### `stocks/stock.py` — `Stock`

Поля: `tg_id`, `stock_type` ("fix"/"percent"), `value`, `is_active`, `valid_until`, `created_at`.

Свойство: `is_valid` — проверяет активность и срок действия.

### `referrals/`

| Модель | Ключевые поля |
|-------|------------|
| `Referral` | `referral_id`, `referrer_id`, `token`, `discount_percent`, `max_usages`, `current_usages`, `is_active` |
| `ReferralLink` | `referrer_tg_id`, `token` |
| `ReferralReward` | `referrer_tg_id`, `reward_type`, `reward_value`, `is_claimed` |
| `ReferralRedemption` | `referral_link_id`, `referred_tg_id`, `redeemed_at` |

### `cache.py`

| Модель | Описание |
|-------|-------------|
| `CacheItem` | Универсальное хранилище кэша: `value`, `expires_at` |
| `REGISTRATE_USER` | Временное состояние регистрации: `tg_id`, `is_msg` |

### `mass_mailing.py` — `MassMailing`

Поля: `id`, `title`, `emoji`.

---

## `services/core/`

Слой бизнес-логики бота (UI-helpers и local cache only). Вся тяжёлая логика (создание/продление ключей, платежи, синхронизация) переехала в backend.

### `data/` ⚠️ Legacy

| Файл | Класс | Описание |
|------|-------|-------------|
| `base.py` | `BaseData[T]` | Универсальный асинхронный CRUD, объединяющий кэш и базу данных |
| `service.py` | `ServiceDataModel` | Фасад, объединяющий экземпляры BaseData для всех типов моделей |
| `protocols.py` | `DataProtocol[T]` | Протокол, определяющий интерфейс доступа к данным |

> Используется backend'ом. В боте данные приходят через `BackendAPIClient`.

### `keys/` (UI layer only)

| Файл | Класс | Описание |
|------|-------|-------------|
| `service.py` | `KeyService` | Подготавливает данные ключа для UI диалога со статистикой трафика |
| `models/key_model.py` | `KeyModel` | Доменная модель с вычисляемыми свойствами: `is_expired`, `days_left`, `hours_left`, `status`, `usage_percent`, `progress_bar` |
| `view/key_view.py` | `KeyView` | Статические методы для отображения успешных/ошибочных ответов |
| `controllers/key_controller.py` | `KeyController` | MVC-контроллер |

**❌ Удалены:** `utils/calculator.py`, `utils/create_key.py`, `utils/formtion.py`, `utils/renewal.py`, `utils/updating.py` — создание/продление ключей теперь в backend.

### `payment/` ❌ Удалён

Модуль платежей (`PaymentProcessor`, `KeyCreationService`, `KeyRenewalService`, `PaymentRouter`) удалён из бота. Вся платёжная логика — в backend.

### `user/`

| Файл | Класс | Описание |
|------|-------|-------------|
| `utils/trial.py` | `TrialService` | Устанавливает trial=1 для пользователя (через backend API) |
| `utils/saturation.py` | `SaturationUser` | Агрегирует полный контекст пользователя из cache |
| `utils/checked_admin.py` | `CheckedUser` | Проверка привилегий администратора через конфигурацию ADMIN_ID |
| `utils/auto_register.py` | `AutoRegistrationService` | Автоматическая регистрация через backend API |

**❌ Удалены:** `utils/delete_data.py` (DeleteUser), `utils/saver.py` (SeverUser), `utils/checked_block.py` (BlockUserChecker) — управление пользователями теперь в backend.

### `gift/`

| Файл | Класс | Описание |
|------|-------|-------------|
| `gift_manager.py` | `GiftLinkProvider` | Жизненный цикл подарочной ссылки: создание, погашение (через backend API) |
| `repositories/gen_token.py` | `TokenGen` | Генератор уникального токена подарка с проверкой коллизий |
| `repositories/gen_url.py` | `GiftUrlGenerator` | Форматирование URL подарка |
| `repositories/checker.py` | `CheckerGiftLink` | Проверка подарочной ссылки |

### `segmentation/`

| Файл | Класс | Описание |
|------|-------|-------------|
| `model.py` | `UserSegment` (Enum) | Сегменты: NEW_USER, ACTIVE_TRIAL, ACTIVE_PAID, EXPIRING_SOON, EXPIRED_PAID, INACTIVE, INACTIVE_TRIAL, CHURN_RISK, COLD_LEAD, BLOCKED |
| `base.py` | `BaseCondition`, `Condition` (ABC) | Абстрактная база условий с утилитами фильтрации ключей |
| `ruls.py` | `SimpleCondition`, `UserSegmenter` | Условия на основе правил и сегментация пользователей с кэшированием (5 мин) |
| `manager.py` | `SegmentationManager` | Пакетная сегментация пользователей: группирует пользователей по сегментам |

**Фабрики условий:** `new_user_condition()`, `expiring_keys_condition(hours)`, `inactive_trial_condition()`, `cold_lead_condition()`, `blocked_condition()`.

### `tariff/data.py` — `TariffData`

Метод: `get(user_id, checked_user)` — возвращает все тарифы для администраторов, отфильтрованный список для пользователей (из cache).

### `price/form_price.py` — `Pricing`

Метод: `formating(price, stock)` — применяет скидку, если акция действительна.

### `connect_module/repositories/form_data.py` ❌ Удалён

`FormConnectionData` удалён — данные для подключения теперь приходят из backend API.

### `time_helper.py` ❌ Удалён

`TimeHelper` удалён — утилиты времени теперь в backend.

---

## `services/cache/`

Система кэширования в памяти с TTL.

| Файл | Класс | Описание |
|------|-------|-------------|
| `storage.py` | `CacheStorage` | Потокобезопасное хранилище с автоматическим истечением TTL (очистка каждые 5 мин) |
| `service.py` | `ModelCache[T]`, `CacheService` | Универсальный типизированный кэш + фасад-одиночка с кэшами, разделёнными по сущностям |
| `protocols.py` | `CacheProtocol[T]` | Интерфейс: `set`, `get`, `delete`, `all`, `keys`, `temporary_set`, `temporary_get` |
| `factory.py` | `LoaderFactory` | Фабрика для загрузки данных репозитория в кэш |
| `loader.py` | `LoadingService` | Предварительная загрузка данных БД в кэш при запуске |

**Свойства CacheService:** `users`, `keys`, `servers`, `tariffs`, `gifts`, `inbounds`, `payments`, `stocks`.

---

## `services/conteiner/`

Внедрение зависимостей через библиотеку `punq`.

| Файл | Описание |
|------|-------------|
| `app.py` | `get_container()` — точка входа как одиночка |
| `protocol.py` | `ContainerProtocol` — интерфейс регистратора |
| `__init__.py` | `create_container()` — оркестрирует все регистрации |

### `registrate/core/` — Регистраторы сервисов

| Файл | Регистрирует (одиночки) |
|------|-----------------------|
| `coreservice.py` | `LoadingService` |
| `cache.py` | `CacheStorage`, `CacheService`, `LoadingService`, `CacheMiddleware` |
| `users.py` | `CheckedUser`, `SaturationUser`, `TrialService` |
| `keys.py` | `KeyService`, `KeyModel` (UI helpers only) |
| `gift.py` | `CheckerGiftLink`, `TokenGen`, `GiftLinkProvider` |
| `tariff.py` | `Pricing`, `TariffData` |
| `backend_client.py` | `BackendAPIClient` |
| `payment.py` | ❌ Пустая заглушка (логика в backend) |

---

## `api/` — BackendAPIClient

HTTP-клиент для взаимодействия с backend API. Единственный источник бизнес-данных для бота.

| Файл | Класс | Описание |
|------|-------|-------------|
| `backend_client.py` | `BackendAPIClient` | Асинхронный httpx-клиент. Все запросы с заголовком `X-Bot-Secret` |
| `schemas.py` | `RegisterFromInviteRequest`, `RegisterFromInviteResponse` | DTO для регистрации |

**Основные методы BackendAPIClient:**
- `register_user(tg_id, ...)` — регистрация пользователя
- `get_user(tg_id)` — получение данных пользователя
- `get_user_keys(tg_id)` — список ключей
- `create_trial_key(tg_id)` — создание пробного ключа
- `delete_key(email)` — удаление ключа
- `renew_key(email, tariff_id, months)` — продление ключа
- `list_tariffs()` — список тарифов
- `initiate_payment(tg_id, tariff_id, operation)` — создание платежа
- `get_payment_status(payment_id)` — статус платежа

---

## `services/synchron/` ❌ Удалён

> Весь модуль синхронизации (`cache_comparator.py`, `xui_fetcher.py`, `key_creator.py`, `traffic.py`, `database_synchronizer.py`) переехал в `backend/services/synchron/` и `backend/background/scheduler.py`.

---

## `services/notification/` ❌ Удалён

> Вся система уведомлений и воронок (`core.py`, `manager.py`, `funnels/*`, `utils/*`) переехала в `backend/`. Запускается через `backend/background/scheduler.py`.

---

## `services/scenarios/`

Оркестраторы бизнес-процессов.

| Файл | Класс | Описание |
|------|-------|-------------|
| `factory_scenario.py` | `ScenarioFactory` (ABC) | Абстрактный: `start()`, `can_handle()`, `get_data()` |
| `create_first_key_scenario.py` | `CreateFerstKeyScenario` | Создаёт первый пробный ключ для нового пользователя |
| `gift_scenario.py` | `GiftActivationScenario` | Активирует подарочные ссылки и создаёт связанный ключ |

---

## `services/billing/` ❌ Удалён

> `stocs_service.py`, `tariff_service.py`, `referral_service.py`, `payment_service.py` удалены. Логика ценообразования и акций — в backend.

---

## `services/analytics/` ❌ Удалён

> Весь модуль аналитики (`funnel_analytics.py`, `conversions.py`, `dashboard_metrics.py`, `ltv_metrics.py`, `churn_metrics.py`, `referral_metrics.py`, `gift_metrics.py`, `payment_metrics.py`) удалён из бота. Аналитика теперь в backend/admin API.

---

### Основные сервисы

| Файл | Класс | Описание |
|------|-------|----------|
| `funnel_analytics.py` | `FunnelAnalytics` | Статистика по воронкам уведомлений |
| `conversions.py` | `ConversionMetricsService` | Метрики конверсии (регистрации, оплаты) |
| `dashboard_metrics.py` | `DashboardMetricsService` | Данные для дашбордов (пользователи, ключи, выручка) |
| `ltv_metrics.py` | `LtvMetricsService` | Lifetime Value — пожизненная ценность пользователя |
| `churn_metrics.py` | `ChurnMetricsService` | Анализ оттока пользователей |
| `referral_metrics.py` | `ReferralMetricsService` | Статистика реферальной программы |
| `gift_metrics.py` | `GiftMetricsService` | Эффективность подарочных ссылок |
| `payment_metrics.py` | `PaymentMetricsService` | **Статистика выручки и прогнозы** |

### PaymentMetricsService — Прогнозирование выручки

**Ключевые возможности:**
- Статистика выручки за год/месяц/неделю/день
- Прогнозы на основе скользящего среднего и линейной регрессии
- Комбинированный метод (60% moving_avg + 40% regression)
- Расчёт уверенности прогноза (0-100%)
- Анализ тренда роста/падения

**Модели данных:**
```python
RevenueStats        # Выручка по периодам + средние чеки
RevenueForecast     # Прогноз с уверенностью и методом
WeeklyRevenue       # Выручка за одну неделю
MonthlyRevenue      # Выручка за один месяц
```

**Методы:**
- `get_revenue_stats()` — статистика из БД (year, month, week, day)
- `forecast_revenue()` — прогноз на неделю и месяц
- `_get_weekly_revenue(weeks)` — история по неделям
- `_get_monthly_revenue(months)` — история по месяцам
- `_forecast_single_value()` — комбинированный прогноз
- `_linear_regression()` — расчёт тренда
- `_calculate_confidence()` — уверенность прогноза
- `_calculate_growth_trend()` — процент роста/падения

### Использование в админ-панели

`PaymentMetricsService` используется через `PaymentStatsGetter` для отображения финансовой статистики в админ-панели:

```python
# В DI контейере
container.register(PaymentMetricsService, factory=lambda: PaymentMetricsService(db_pool))
container.register(PaymentStatsGetter, factory=lambda: PaymentStatsGetter(payment_metrics))

# В админ-диалоге
stats = await payment_metrics.get_revenue_stats()
forecast = await payment_metrics.forecast_revenue()
```

**Прогнозирование:**
- Использует данные за последние 8 недель и 6 месяцев
- Автоматически выбирает метод (moving_avg, regression, combined)
- Показывает уверенность (🟢 >70%, 🟡 >40%, 🔴 <40%)
- Рассчитывает тренд роста в процентах

---

## `dialogs/`

Компоненты UI и диалогов aiogram-dialog.

### Основные файлы диалогов

| Файл | Описание |
|------|-------------|
| `setup.py` | Регистрация маршрутизатора диалога |
| `loader.py` | Загрузчик YAML-схем для определений диалогов |
| `dialog_factory.py` | Фабрика для создания экземпляров Dialog из схем |
| `conditions.py` | Условная видимость для виджетов диалога |
| `main_dialog.py` | Диалог главного меню (приветствие, профиль) |
| `key_dialog.py` | Диалог управления ключами (просмотр, создание, удаление, продление) |
| `gift_dialog.py` | Диалог подарочных ссылок |
| `partner_dialog.py` | Диалог партнёра/реферала |
| `registration.py` | Диалог регистрации |
| `instruction.py` | Диалог инструкций клиента VPN (Android, iOS, Windows, Linux) |
| `usage_rules.py` | Диалог правил использования в несколько страниц |

### `admin/`

| Файл | Описание |
|------|-------------|
| `adminpanel.py` | Основной диалог панели администратора |
| `admin_key_manager.py` | Управление ключами администратора (редактирование, удаление, изменение тарифа) |
| `admin_user_profile.py` | Просмотр профиля пользователя администратором |
| `admin_registration.py` | Регистрация пользователя администратором |
| `mass_mailing.py` | Диалог массовой рассылки |
| `search_dialog.py` | Диалог поиска пользователя |

### `messages/`

Вложенные шаблоны сообщений для разных контекстов:

| Путь | Описание |
|------|-------------|
| `users/welcom/first_msg.py` | Приветственное сообщение для новых пользователей |
| `users/profile/main_menu.py` | Сообщение профиля/главного меню |
| `users/tariff/tariff.py` | Сообщение отображения тарифа |
| `users/payments/payment.py` | Инструкции по оплате |
| `users/instructions/instructions.py` | Инструкции по настройке VPN |
| `users/rules/usage_rules.py` | Текст правил использования |
| `users/gift/gift_activated.py` | Сообщение активации подарка |
| `users/error_msg/bot_errors.py` | Сообщения об ошибках |
| `users/reminder/discount_reminder.py` | Напоминание о скидке |
| `stats.py` | Отображение статистики |

### `templates/`

Повторно используемые шаблоны диалогов:

| Файл | Класс | Описание |
|------|-------|-------------|
| `confirmation.py` | `ConfirmationTemplate` | Диалог подтверждения Да/Нет |
| `instruction_step.py` | `InstructionStepTemplate` | Пошаговая инструкция |
| `list_view.py` | `ListViewTemplate` | Прокручиваемый список |

### `windows/`

Система окон на основе компонентов:

| Файл | Описание |
|------|-------------|
| `base.py` | `MessageBuilder` (ABC), `KeyboardBuilder` (ABC), `GetterBuilder` (ABC) — базовые интерфейсы |
| `window_factory.py` | `WindowFactory` — создаёт Window из билдеров сообщения + клавиатуры + получения данных |

#### `windows/getters/`

| Путь | Класс | Описание |
|------|-------|-------------|
| `profile/main.py` | `ProfileGetter` | Загружает данные пользователя для отображения профиля |
| `gift/main.py` | `GiftGetter` | Загружает данные подарочной ссылки |
| `tariff/preview.py` | `TariffPreviewGetter` | Загружает список тарифов для предварительного просмотра |
| `payment/form_pay.py` | `FormPayGetter` | Данные формы оплаты |
| `payment/setting_payment.py` | `SettingPaymentGetter` | Данные настроек оплаты |

#### `windows/widgets/message/`

| Путь | Класс | Описание |
|------|-------|-------------|
| `profile/main.py` | `ProfileMessage` | Отображаемый текст профиля |
| `profile/welcom.py` | `WelcomeMessage` | Приветственный текст с предложением триала |
| `gift/main.py` | `GiftMessage` | Отображение подарочной ссылки |
| `tariff/preview.py` | `TariffPreviewMessage` | Рендеринг списка тарифов |
| `payment/form_pay.py` | `FormPayMessage` | Текст формы оплаты |
| `payment/setting_pay.py` | `SettingPayMessage` | Текст настроек оплаты |
| `payment/view_tariff.py` | `ViewTariffMessage` | Отображение деталей тарифа |

---

## `middlewares/`

См. [docs/MIDDLEWARES_MODULE.md](MIDDLEWARES_MODULE.md) — актуальный стек middleware после рефакторинга.

---

## `states/`

См. [docs/STATES_MODULE.md](STATES_MODULE.md) — FSM-состояния диалогов.

---

## `registration/`

См. [docs/REGISTRATION_MODULE.md](REGISTRATION_MODULE.md) — логика регистрации (теперь через backend API).

---

## `handlers/`

Обработчики aiogram (start, admin, instructions, keys). Маршрутизируют события в диалоги.

---

## `utils_bot/`

Утилиты бота: логирование, форматирование, валидаторы.

---

## `core/`

Конфигурация, константы, исключения проекта.