# Документация по модулям — Bot_3xui_vpn

Telegram-бот (aiogram 3) для управления подписками на VPN через панель 3x-ui. Обрабатывает регистрацию пользователей, управление ключами, оплату (YooKassa), подарочные ссылки, реферальную систему, тарифы и административные функции.

---


## Содержание

- [Корневые модули](#root-modules)
- [database/](#database)
- [models/](#models)
- [services/core/](#servicescore)
- [services/cache/](#servicescache)
- [services/conteiner/](#servicesconteiner)
- [services/synchron/](#servicessynchron)
- [services/notification/](#servicesnotification)
- [services/scenarios/](#servicesscenarios)
- [services/billing/](#servicesbilling)
- [services/analytics/](#servicesanalytics)
- [dialogs/](#dialogs)
- [getters/](#getters)
- [handlers/](#handlers)
- [middlewares/](#middlewares)
- [states/](#states)
- [registration/](#registration)
- [payments/](#payments) — Модуль для работы с платежами через ЮKassa. Документация: [PAYMENTS_MODULE.md](PAYMENTS_MODULE.md)
- [widgets/](#widgets)
- [utils_bot/](#utils_bot)
- [core/](#core)

---

## Корневые модули

### `main.py`

Точка входа. Организует запуск бота, регистрацию middleware и опрос.

| Функция | Описание |
|----------|-------------|
| `run_webhook_server()` | Запускает сервер aiohttp webhook для YooKassa |
| `on_startup()` | Инициализирует кэш, загружает данные БД, запускает фоновые задачи |
| `setup_middlewares()` | Регистрирует стек middleware: Database → Cache → XUI → Registration → Logging → DialogErrorHandler |
| `main()` | Основная асинхронная точка входа — настройка, включение маршрутизатора, опрос бота |

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

### `client.py`

Обёртка клиента для панели 3x-ui с логикой повтора.

| Класс | Описание |
|-------|-------------|
| `XUIRetryPolicy` | Статическая утилита для повторяемых исключений и логирования повторов |
| `XUISession` | Основная обёртка клиента вокруг `py3xui.AsyncApi` |

**Методы XUISession:**

| Метод | Описание |
|--------|-------------|
| `server_init()` | Загружает конфигурацию сервера, создаёт экземпляр AsyncApi |
| `ensure_auth()` | Обеспечивает аутентификацию на панели |
| `add_client()` | Добавляет VPN-клиента (повтор=3, ожидание=2с) |
| `extend_client_key()` | Обновляет срок действия клиента и квоту трафика |
| `delete_client()` | Удаляет клиента с панели |
| `get_inbounds()` | Получает список входящих соединений |
| `get_traffic()` | Получает информацию о трафике клиента |
| `delete_old_client()` | Пакетно удаляет просроченных клиентов (>30 дней) |

### `tasks.py`

Менеджер фоновых асинхронных задач.

| Класс/Метод | Описание |
|--------------|-------------|
| `BackgroundTaskManager` | Организует фоновые операции |
| `start_sync_cache()` | Синхронизирует кэш каждые 3 часа (5 мин при ошибке) |
| `start_notification_bot()` | Запускает воронку уведомлений каждые 3600с |
| `run_webhook_server()` | Запускает webhook aiohttp для платежей |
| `start_all_tasks()` | Создаёт все асинхронные задачи |
| `stop_all_tasks()` | Отменяет и ожидает все задачи |

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

Система мониторинга Prometheus (~30 метрик). Подробная документация: [docs/METRICS_MODULE.md](METRICS_MODULE.md).

| Компонент | Описание |
|-----------|-------------|
| `registry.py` | Единый реестр всех Counter/Gauge/Histogram метрик |
| `setup.py` | Инициализация Collector'ов и запуск HTTP сервера |
| `http_server.py` | GET `/metrics` endpoint для Prometheus scraping |
| `collectors/cache_collector.py` | Pull-модель: размеры кеша по namespace |
| `collectors/db_pool_collector.py` | Pull-модель: asyncpg pool (size/idle/used) |

**Категории метрик:** Business (платежи, ключи, регистрации, уведомления), Infrastructure (DB pool, кеш, XUI API, Telegram), Background tasks.

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

## `database/`

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

Слой бизнес-логики.

### `data/`

| Файл | Класс | Описание |
|------|-------|-------------|
| `base.py` | `BaseData[T]` | Универсальный асинхронный CRUD, объединяющий кэш и базу данных |
| `service.py` | `ServiceDataModel` | Фасад, объединяющий экземпляры BaseData для всех типов моделей |
| `protocols.py` | `DataProtocol[T]` | Протокол, определяющий интерфейс доступа к данным |

**Методы BaseData[T]:** `get_data()`, `get_all()`, `exists()`, `count()`, `save_data()`, `delete_data()`, `get_by()`, `update()`.

### `keys/`

| Файл | Класс | Описание |
|------|-------|-------------|
| `service.py` | `KeyService` | Подготавливает данные ключа для UI диалога со статистикой трафика |
| `models/key_model.py` | `KeyModel` | Доменная модель с вычисляемыми свойствами: `is_expired`, `days_left`, `hours_left`, `status`, `usage_percent`, `progress_bar` |
| `view/key_view.py` | `KeyView` | Статические методы для отображения успешных/ошибочных ответов |
| `controllers/key_controller.py` | `KeyController` | MVC-контроллер, координирующий сервис, модель, представление |
| `utils/calculator.py` | `ExpiryCalculator` | Вычисляет метки времени окончания для новых ключей и продлений |
| `utils/create_key.py` | `CreateKey` | Оркестратор рабочего процесса создания ключа |
| `utils/formtion.py` | `FormationKey` | Построение объекта ключа с генерацией email/client_id |
| `utils/renewal.py` | `KeyRenewal` | Продление ключа через панель XUI + синхронизация с БД |
| `utils/updating.py` | `KeyUpdater` | Применяет параметры тарифа к ключу |

### `payment/`

| Файл | Класс | Описание |
|------|-------|-------------|
| `processor.py` | `PaymentProcessor` | Загружает данные платежа, проверяет, извлекает тип операции |
| `creation_service.py` | `KeyCreationService` | Создаёт и доставляет новый ключ после оплаты |
| `renewal_service.py` | `KeyRenewalService` | Увеличивает срок действия ключа после оплаты |
| `router.py` | `PaymentRouter` | Маршрутизирует платежи к обработчикам create_key или renew_key |

### `user/`

| Файл | Класс | Описание |
|------|-------|-------------|
| `utils/trial.py` | `TrialService` | Устанавливает trial=1 для пользователя |
| `utils/delete_data.py` | `DeleteUser` | Каскадное удаление: ключи XUI + пользователь БД |
| `utils/saturation.py` | `SaturationUser` | Агрегирует полный контекст пользователя (пользователь + сервер + ключи) |
| `utils/saver.py` | `SeverUser` | Регистрация и сохранение пользователя |
| `utils/checked_admin.py` | `CheckedUser` | Проверка привилегий администратора через конфигурацию ADMIN_ID |
| `utils/checked_block.py` | `BlockUserChecker` | Помечает заблокированных пользователей при ошибке TelegramForbiddenError |

### `gift/`

| Файл | Класс | Описание |
|------|-------|-------------|
| `gift_manager.py` | `GiftLinkProvider` | Жизненный цикл подарочной ссылки: создание, погашение |
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

Метод: `get(user_id, checked_user)` — возвращает все тарифы для администраторов, отфильтрованный список для пользователей.

### `price/form_price.py` — `Pricing`

Метод: `formating(price, stock)` — применяет скидку, если акция действительна.

### `connect_module/repositories/form_data.py` — `FormConnectionData`

Метод: `data(user_id, server_id)` — возвращает `{api_url, login, password, inbound_id, subscription_url}`.

### `time_helper.py` — `TimeHelper`

Утилиты меток времени в миллисекундах с кэшированием: `now_ms`, `two_days_ago_ms`, `twenty_four_hours_ms`, `ten_hours_ms`, `seventy_two_hours_ms`.

Функция: `valid_24h_keys(key)` — проверяет, заканчивается ли ключ в течение 24 часов.

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
| `coreservice.py` | `DataService`, `ServiceDataModel`, `LoadingService`, `XUISession` |
| `cache.py` | `CacheStorage`, `CacheService`, `LoadingService`, `CacheMiddleware` |
| `users.py` | `CheckedUser`, `SaturationUser`, `TrialService`, `DeleteUser` |
| `keys.py` | `ExpiryCalculator`, `KeyUpdater`, `FormConnectionData`, `FormationKey`, `CreateKey`, `KeyRenewal` |
| `gift.py` | `CheckerGiftLink`, `TokenGen`, `GiftLinkProvider` |
| `tariff.py` | `Pricing`, `TariffData` |
| `payment.py` | Пустая заглушка |

---

## `services/synchron/`

Синхронизация с панелью XUI.

| Файл | Класс | Описание |
|------|-------|-------------|
| `cache_comparator.py` | `CacheComparator` | Сравнивает данные панели XUI с кэшем, используя разность множеств |
| `xui_fetcher.py` | `XUIFetcher` | Получает и проверяет клиентов с панели XUI |
| `key_creator.py` | `KeyCreator` | Создаёт объекты Key из клиентов XUI, сохраняет в БД |
| `traffic.py` | `TrafficUpdater` | Асинхронное пакетное получение/обновление статистики трафика с ограничением скорости через семафор |
| `database_synchronizer.py` | `DatabaseSynchronizer` | Основной оркестратор: получение → сравнение → восстановление отсутствующих → обновление трафика пакетами |

---

## `services/notification/`

Многоуровневая система уведомлений.

### `core.py`

| Компонент | Описание |
|-----------|-------------|
| `FunnelType` (Enum) | KEY_EXPIRY_24H, KEY_EXPIRY_10H, TRIAL_REMINDER |
| `NotificationCondition` (ABC) | Абстрактная база условий |
| `SimpleCondition` | Декларативное условие через список правил |
| `UserSegmenter` | Определяет сегмент пользователя с кэшированием 5 мин |
| `FunnelStrategy` (ABC) | Базовая воронка: `should_send()`, `build_message()`, `build_keyboard()`, `process()` |

### `manager.py` — `FunnelManager`

Методы: `register_funnel()`, `process_all(bot)` — проходит пользователей через все воронки, отслеживает статистику.

### `funnels/`

| Файл | Класс | Триггер |
|------|-------|---------|
| `key_expiry.py` | `KeyExpiryFunnel` | Ключи, заканчивающиеся через 24ч/10ч |
| `trial_reminder.py` | `TrialReminderFunnel` | Новые пользователи (сегмент=NEW_USER), предложение 7-дневного бесплатного триала |
| `referral_bonus.py` | `ReferralBonusFunnel` | Реферальная скидка для новых пользователей |
| `cold_lead_engagement.py` | `ColdLeadEngagementFunnel` | Финальное напоминание для неактивных пользователей (сегмент=COLD_LEAD) |

### `utils/`

| Файл | Класс | Описание |
|------|-------|-------------|
| `message_builder.py` | `MessageBuilder` | Шаблоны: key_expiry, trial_reminder, referral, upsell, winback, cross_sell |
| `keyboard_builder.py` | `KeyboardBuilder` | Инлайн-клавиатуры для каждого типа воронки |

---

## `services/scenarios/`

Оркестраторы бизнес-процессов.

| Файл | Класс | Описание |
|------|-------|-------------|
| `factory_scenario.py` | `ScenarioFactory` (ABC) | Абстрактный: `start()`, `can_handle()`, `get_data()` |
| `create_first_key_scenario.py` | `CreateFerstKeyScenario` | Создаёт первый пробный ключ для нового пользователя |
| `gift_scenario.py` | `GiftActivationScenario` | Активирует подарочные ссылки и создаёт связанный ключ |

---

## `services/billing/`

Ценообразование и акции (частично реализовано).

| Файл | Класс | Описание |
|------|-------|-------------|
| `stocs_service.py` | `StockManager` | Проверяет активность акции, лимиты, размер скидки |
| `tariff_service.py` | `TariffManager` | Получает тариф из кэша/БД, применяет скидки рефералов/акций |
| `referral_service.py` | `ReferralManager` | Заглушка для данных рефералов |
| `payment_service.py` | — | Пусто |

---

## `services/analytics/`

Аналитика и сбор метрик для бизнес-анализа и прогнозирования.

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
| `payment/view_tar