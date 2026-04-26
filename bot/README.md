# VPN Bot 3x-ui

Telegram-бот для управления VPN-подписками через панель [3x-ui](https://github.com/MHSanaei/3x-ui). Построен на **aiogram 3** + **aiogram-dialog**, полностью асинхронный.

## Возможности

- Регистрация пользователей с пробным периодом
- Создание, продление и удаление VPN-ключей
- Оплата подписок через YooKassa (webhook)
- Система тарифов со скидками за объём
- Реферальная программа (3 уровня: 10%, 5%, 2%)
- Подарочные ссылки
- Админ-панель: расширенная статистика, поиск, рассылка, сегментация ключей
  - **Статистика пользователей**: регистрации, отток, заблокированные
  - **Статистика ключей**: разбивка по тарифам, 24h мониторинг, уведомления
  - **Финансовая статистика**: выручка, прогнозы, тренды
- Уведомления об истечении ключей (воронки)
- Автосинхронизация с 3x-ui панелью
- Кеширование данных в памяти с TTL
- **Аналитика и прогнозирование**:
  - Прогнозы выручки (скользящее среднее + линейная регрессия)
  - Метрики конверсии, LTV, оттока
  - Анализ реферальной программы и подарочных ссылок

## Требования

- Python 3.11+
- PostgreSQL 14+
- Панель 3x-ui
- Telegram Bot Token ([@BotFather](https://t.me/BotFather))
- YooKassa аккаунт (для платежей)

## Быстрый старт

### 1. Клонирование и установка

```bash
git clone <repository-url>
cd bot_3xui
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Настройка окружения

Создайте файл `.env` в корне проекта:

```env
# === Обязательные ===
BOT_TOKEN=7780059989:AAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
ADMIN_ID=[123456789]
DATABASE_URL=postgresql://user:password@localhost:5432/bot_db
AVAILABLE_CONNECTIONS="[11, 12]"
AVAILABLE_RATES="[9, 8, 7]"
PAYMENT_INFO={}

# === База данных ===
DB_NAME=bot_db
DB_USER=user
DB_PASSWORD=password

# === 3x-ui панель ===
API_URL=http://your-panel:2095
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin_password

# === YooKassa (опционально) ===
YOOKASSA_SHOP_ID=123456
YOOKASSA_SECRET_KEY=test_xxxxxxxxxxxxx

# === Webhook для YooKassa ===
WEBHOOK_HOST=0.0.0.0
WEBHOOK_PORT=8080
WEBHOOK_PATH=/yookassa_webhook
DISABLE_WEBHOOK_IP_CHECK=false

# === Бот ===
BOT_NAME=MyVPNBot
URL_BOT=https://t.me/MyVPNBot
DEFAULT_PRICING_PLAN=10
TRIAL_TIME=30

# === Поддержка ===
CHANNEL_URL=https://t.me/my_channel
TECHNICAL_SUPPORT=123456789
SUPPORT_CHAT_URL=https://t.me/support_chat
```

Полный список переменных — в [`config.py`](config.py).

### 3. Создание базы данных

```bash
createdb bot_db
# или
psql -c "CREATE DATABASE bot_db;"
```

### 4. Запуск

```bash
python main.py
```

## Docker

### Запуск с Docker Compose (бот + PostgreSQL)

Если нужна БД в контейнере, добавьте сервис `db` в `docker-compose.yml`:

```yaml
services:
  db:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${DB_NAME}
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER} -d ${DB_NAME}"]
      interval: 5s
      timeout: 3s
      retries: 5

  bot:
    build: .
    restart: unless-stopped
    depends_on:
      db:
        condition: service_healthy
    env_file: .env
    environment:
      DATABASE_URL: postgresql://${DB_USER}:${DB_PASSWORD}@db:5432/${DB_NAME}
    ports:
      - "${WEBHOOK_PORT:-8080}:${WEBHOOK_PORT:-8080}"
    volumes:
      - ./logs:/app/logs
      - ./logs_error:/app/logs_error
      - ./video_instructions:/app/video_instructions:ro

volumes:
  pgdata:
```

### Запуск только бота (БД уже есть)

Текущий `docker-compose.yml` настроен именно для этого случая:

```bash
docker-compose up -d --build
```

В `.env` укажите `DATABASE_URL` с `host.docker.internal`:

```env
DATABASE_URL=postgresql://user:password@host.docker.internal:5432/bot_db
```

### Полезные команды

```bash
docker-compose up -d --build   # Собрать и запустить
docker-compose logs -f bot     # Логи бота
docker-compose down            # Остановить
docker-compose exec bot bash   # Зайти в контейнер
```

## Команды разработки

```bash
make lint          # Проверка кода (ruff)
make formatting    # Автоформатирование (ruff)
make test          # Запуск всех тестов
make test-fast     # Тесты с остановкой при первой ошибке
make test-cov      # Тесты с отчётом покрытия (HTML)
make test-module MODULE=models  # Тесты конкретного модуля
make ci            # CI-проверка (coverage >= 75%)
```

Дополнительно:

```bash
vulture . --min-confidence 100  # Поиск мёртвого кода
mypy .                          # Проверка типов
```

## Архитектура

### Структура проекта

```
bot_3xui/
├── main.py                 # Точка входа
├── config.py               # Конфигурация из .env
├── bot_project.py          # Инициализация Bot и Dispatcher
├── client.py               # Клиент 3x-ui панели (py3xui)
├── tasks.py                # Фоновые задачи
├── logger.py               # Структурированное логирование
│
├── models/                 # Модели данных (User, Key, Server, Tariff, ...)
├── database/               # Слой БД (asyncpg, репозитории)
├── services/               # Бизнес-логика
│   ├── cache/              # Кеширование (CacheService, CacheKeyManager)
│   ├── core/               # Ядро (ключи, пользователи, платежи, подарки)
│   ├── conteiner/          # DI-контейнер (punq)
│   ├── notification/       # Воронки уведомлений
│   └── scenarios/          # Бизнес-сценарии
│
├── handlers/               # Обработчики Telegram-сообщений
├── middlewares/             # Стек middleware
├── states/                 # FSM-состояния диалогов
├── dialogs/                # UI-компоненты (aiogram-dialog)
├── filters/                # Фильтры сообщений
├── getters/                # Геттеры данных для диалогов
├── registration/           # Логика регистрации
├── payments/               # Интеграция YooKassa
│
├── tests/                  # Тесты (pytest)
├── docs/                   # Документация
├── Dockerfile
└── docker-compose.yml
```

### Стек middleware (порядок критичен)

```
DatabaseMiddleware → CacheMiddleware → XUIMiddleware
  → RegistrationUsersMiddleware → LoggingMiddleware
    → DialogExceptionHandlerMiddleware
```

### Поток данных

```
CacheService (in-memory) → DataService (asyncpg) → BaseRepository[T] → PostgreSQL
                                                  → XUISession → 3x-ui Panel
```

### Фоновые задачи

| Задача | Интервал | Описание |
|--------|----------|----------|
| Синхронизация кеша | 3 часа | Обновление кеша из БД и 3x-ui |
| Воронки уведомлений | 1 час | Напоминания об истечении ключей |
| Webhook-сервер | постоянно | Приём платежей YooKassa |

## Документация

Подробная документация в директории [`docs/`](docs/):

| Файл | Описание |
|------|----------|
| [modules.md](docs/modules.md) | Обзор архитектуры |
| [database.md](docs/database.md) | Слой базы данных |
| [MODELS_MODULE.md](docs/MODELS_MODULE.md) | Модели данных |
| [DIALOGS_MODULE.md](docs/DIALOGS_MODULE.md) | Система диалогов |
| [ADMIN_DIALOGS.md](docs/ADMIN_DIALOGS.md) | Админ-панель и статистика |
| [MIDDLEWARES_MODULE.md](docs/MIDDLEWARES_MODULE.md) | Стек middleware |
| [PAYMENTS_MODULE.md](docs/PAYMENTS_MODULE.md) | Интеграция YooKassa |
| [REGISTRATION_MODULE.md](docs/REGISTRATION_MODULE.md) | Поток регистрации |
| [NOTIFICATION_MODULE.md](docs/NOTIFICATION_MODULE.md) | Воронки уведомлений |
| [SYNC_MODULE.md](docs/SYNC_MODULE.md) | Синхронизация с панелью |
| [KEY_SEGMENTATION.md](docs/KEY_SEGMENTATION.md) | Сегментация ключей |
| [TESTS_MODULE.md](docs/TESTS_MODULE.md) | Руководство по тестам |
| [services.md](docs/services.md) | Бизнес-сервисы |
| [LOGGING.md](docs/LOGGING.md) | Настройка логирования |

## Логирование

- `logs/application.log` — INFO-уровень, ротация 14 дней
- `logs_error/errors.log` — ERROR-уровень, ротация 28 дней
- Автоматическое маскирование чувствительных данных
- Ежедневная ротация с ZIP-сжатием

## Лицензия

Private repository. All rights reserved.
