# Документация по модулю database

Модуль `database` предоставляет абстракцию для работы с базой данных в проекте Bot_3xui_vpn. Он реализует слой доступа к данным с использованием паттерна Repository и библиотеки asyncpg для асинхронного взаимодействия с PostgreSQL.

## Структура модуля

```
database/
├── __init__.py
├── base.py
├── protocols.py
├── service.py
└── auth/
    ├── __init__.py
    ├── repositories.py
    └── services.py
```

## Основные компоненты

### `base.py`

Содержит базовые классы для работы с базой данных.

#### `create_db_pool()`
Функция для создания пула соединений с базой данных. Использует параметры из конфигурации `DATABASE_URL`.

#### `BaseRepository[T]`
Базовый универсальный репозиторий, реализующий CRUD-операции для любой модели.

**Методы:**
- `get(pool, **kwargs)` — Получение одной записи по фильтру
- `get_all(pool)` — Получение всех записей
- `create(pool, **kwargs)` — Создание новой записи
- `update(pool, search_data, **kwargs)` — Обновление записи
- `delete(pool, **kwargs)` — Удаление записи

Репозиторий является универсальным (generic) и работает с любым типом модели T.

### `protocols.py`

Определяет протокол `DatabaseProtocol[T]`, который задает контракт интерфейса для всех репозиториев. Это позволяет использовать строгую типизацию и dependency injection.

### `service.py`

Фасад `DataService`, который объединяет все репозитории в одном месте. Предоставляет удобный доступ ко всем сущностям приложения.

**Атрибуты:**
- `users` — Работа с пользователями
- `keys` — Работа с ключами VPN
- `servers` — Работа с серверами
- `payments` — Работа с платежами
- `tariffs` — Работа с тарифами
- `inbounds` — Работа с входящими подключениями
- `gifts` — Работа с подарочными ссылками
- `stocks` — Работа с акциями и скидками

### `auth/`

Специализированные репозитории и сервисы для управления регистрацией пользователей.

#### `repositories.py`
- `AuthRepository` — Репозиторий для таблицы `registrate_msg_user`, управляющий состоянием регистрации пользователя
  - `check_connection_exists()` — Проверка существования пользователя
  - `get_status_msg()` — Получение статуса регистрации
  - `upsert_user_message_status()` — Обновление статуса регистрации

#### `services.py`
- `AuthService` — Сервисный слой для работы с регистрацией, обертывает репозиторий с логированием
  - `check_user_in_db_srv()` — Проверка пользователя в БД
  - `check_connection_exists_srv()` — Проверка существования подключения
  - `get_status_msg_srv()` — Получение статуса сообщения при регистрации
  - `update_user_message_status_srv()` — Обновление статуса регистрации
  - `insert_user_reg()` — Добавление пользователя

Глобальный экземпляр: `auth_srv`

## Модели данных

Модуль работает с моделями из `models/`, которые являются dataclass с сериализацией. Основные модели:

### `User`
Пользователь бота
- `tg_id` — Telegram ID
- `username`, `first_name`, `last_name` — Информация о пользователе
- `is_admin` — Флаг администратора
- `trial` — Статус триала (0/1)
- `server_id` — Назначенный сервер
- `referral_id` — ID реферальной ссылки
- `is_blocked` — Флаг блокировки
- `created_at`, `updated_at` — Метки времени

### `Key`
Ключ VPN
- `tg_id` — Владелец ключа
- `client_id` — ID клиента в 3x-ui
- `email` — Идентификатор клиента
- `expiry_time` — Время истечения (мс)
- `key` — Строка конфигурации
- `inbound_id` — ID входящего соединения
- `total_gb` — Лимит трафика
- `tariff_id`, `name_tariff` — Информация о тарифе
- `used_traffic` — Использованный трафик
- `notified_10h`, `notified_24h` — Флаги уведомлений

### `Server`
Сервер 3x-ui
- `id` — ID сервера
- `cluster_name`, `server_name` — Названия кластера и сервера
- `api_url` — URL API
- `subscription_url` — URL подписки
- `login`, `password` — Учетные данные

### `Inbound`
Входящее соединение
- `server_id` — Ссылка на сервер
- `inbound_id` — ID входящего
- `name_inbound` — Название

### `Tariff`
Тарифный план
- `id` — ID тарифа
- `name_tariff` — Название
- `amount` — Цена
- `description` — Описание
- `limit_ip` — Ограничение IP
- `period` — Период (дней)
- `traffic_limit` — Лимит трафика (ГБ)

### `GiftLink`
Подарочная ссылка
- `sender_tg_id` — Отправитель
- `tariff_id` — ID тарифа
- `token` — Уникальный токен
- `recipient_tg_id`, `email` — Получатель
- `_status` — Статус (active/redeemed)
- `created_at`, `used_at` — Временные метки

### `PaymentModel`
Платеж
- `payment_id` — ID платежа (YooKassa)
- `tg_id` — Пользователь
- `amount` — Сумма
- `payment_type` — Тип операции
- `status` — Статус
- `created_at` — Время создания

### `Stock`
Акция/скидка
- `tg_id` — Пользователь
- `stock_type` — Тип скидки (fix/percent)
- `value` — Значение скидки
- `is_active` — Активность
- `valid_until` — Срок действия
- `created_at` — Время создания

## Принципы работы

1. **Разделение ответственности** — Каждый репозиторий отвечает за одну таблицу
2. **Универсальность** — `BaseRepository` может работать с любой моделью
3. **Типизация** — Использование generics и протоколов для строгой типизации
4. **Безопасность** — Защита от SQL-инъекций через параметризованные запросы
5. **Логирование** — Все операции логируются
6. **Кэширование** — Работает в паре с модулем cache для повышения производительности

## Пример использования

```python
from database import create_db_pool, DataService

# Создание пула соединений
db_pool = await create_db_pool()

# Создание сервиса данных
data_service = DataService()

# Работа с пользователями
user = await data_service.users.get(db_pool, tg_id=123456789)

# Создание нового пользователя
success = await data_service.users.create(
    db_pool,
    tg_id=123456789,
    username="example_user"
)
```
