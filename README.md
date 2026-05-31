<!-- generated-by: gsd-doc-writer -->
# VPN Platform

Монорепо для VPN-сервиса с тремя компонентами: FastAPI-бэкенд (источник истины), Telegram-бот (UI-слой) и веб-интерфейс.

## Архитектура

| Компонент | Путь | Роль | Порт |
|---|---|---|---|
| FastAPI Backend | `backend/` | Бизнес-логика, интеграция с 3x-UI, YooKassa, кеш, фоновые задачи и отправка Telegram-уведомлений | 8000 |
| Telegram Bot | `bot/` | **Pure UI layer**: диалоги, хендлеры, взаимодействие с backend через API | — |
| Web Interface | `web/` | SPA + тонкий FastAPI-прокси поверх backend API | 8001 |

**Контракт:** Бот и веб **не обращаются напрямую к БД** — только через backend API. Вся бизнес-логика (ключи, платежи, тарифы, аналитика, уведомления), интеграция с 3x-UI и YooKassa живут исключительно в `backend/`.

## Требования

- Python 3.11+
- Docker и Docker Compose
- PostgreSQL 16 (запускается через Docker Compose)

## Установка и запуск

### Полный запуск через Docker Compose

```bash
git clone <repository-url>
cd vpn-platform
# Настройте .env файл в корне проекта (см. ниже)
docker-compose up -d
```

Docker Compose поднимает:
- `postgres` — база данных
- `backend` — API на порту 8000
- `bot` — Telegram-бот
- `web` — веб-интерфейс на порту 8000 (внутри сети)
- `nginx` — reverse proxy на портах 80/443

### Запуск по компонентам (разработка)

```bash
# Backend (порт 8000)
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload

# Bot
cd bot && pip install -r requirements.txt
python main.py

# Web (порт 8001)
cd web && pip install -r requirements.txt
uvicorn app.main:app --port 8001 --reload
```

## Конфигурация

Каждый компонент использует переменные окружения из корневого `.env` (при запуске через Docker Compose) или собственного `.env` файла (при локальной разработке).

### backend/.env

| Переменная | Описание |
|---|---|
| `DATABASE_URL` | asyncpg DSN для PostgreSQL |
| `BOT_SECRET_KEY` | Shared secret для аутентификации бота/веба |
| `ADMIN_API_KEY` | API-ключ для административных операций |
| `TELEGRAM_BOT_TOKEN` | Токен бота (для отправки уведомлений из backend) |
| `XUI_API_URL` / `XUI_LOGIN` / `XUI_PASSWORD` | Учётные данные 3x-UI панели |
| `XUI_INBOUND_ID` | ID inbound по умолчанию для новых ключей |
| `YOOKASSA_SHOP_ID` / `YOOKASSA_SECRET_KEY` | Параметры платёжной системы |
| `WEBHOOK_BASE_URL` | Публичный URL для YooKassa-колбэков |
| `WEBHOOK_ALLOWED_IPS` | IP-адреса YooKassa через запятую |
| `ADMIN_TG_IDS` | JSON-массив Telegram ID администраторов |
| `LOG_LEVEL` | Уровень логирования (по умолчанию: INFO) |

### web/.env

| Переменная | Описание |
|---|---|
| `DATABASE_URL` | asyncpg DSN (только таблицы аутентификации) |
| `SECRET_KEY` | Ключ подписи JWT |
| `BOT_SECRET_KEY` | Shared secret с backend |
| `BACKEND_URL` | Базовый URL backend API (по умолчанию: `http://localhost:8000`) |
| `CSRF_ENABLED` | Отключить CSRF для тестов: `false` |

### bot/.env

| Переменная | Описание |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Токен Telegram-бота |
| `BACKEND_URL` | URL backend API (например: `http://localhost:8000`) |
| `BOT_SECRET_KEY` | Shared secret с backend |
| `ADMIN_TG_IDS` | JSON-массив Telegram ID администраторов |

> **Примечание:** Бот больше не требует прямого доступа к БД, 3x-UI или YooKassa. Все данные получаются через backend API.

## Аутентификация между сервисами

| Клиент | Заголовок | Описание |
|---|---|---|
| Бот → Backend | `X-Bot-Secret: <BOT_SECRET_KEY>` | Shared secret |
| Веб → Backend | `X-Bot-Secret: <BOT_SECRET_KEY>` | Shared secret (service-to-service) |
| Веб → Пользователь | JWT в HttpOnly cookie | `access_token` + `refresh_token` |
| Админ → Backend | `X-API-Key: <ADMIN_API_KEY>` | Admin operations |

## API Backend (порт 8000)

Основные группы эндпоинтов под префиксом `/api/v1`:

- `GET|POST|DELETE /keys` — управление VPN-ключами
- `POST /keys/trial` — создание пробного ключа
- `POST /keys/{email}/renew` — продление ключа
- `GET|POST /payments` — история и создание платежей, YooKassa webhook
- `GET /tariffs` — тарифные планы
- `GET|POST /users` — пользователи
- `GET|POST /admin` — здоровье системы, сброс кеша

Полная документация: `/docs` (Swagger UI при запущенном бэкенде).

## Фоновые задачи

APScheduler в `backend/background/scheduler.py` выполняет:

- **Cache Sync** — синхронизация кеша с БД (каждые 3 часа)
- **Panel Sync** — синхронизация с 3x-UI панелью (каждые 3 часа)
- **Notification Funnels** — проверка истекающих ключей и отправка уведомлений (каждый час)

## Кеш и идентификаторы

`CacheService` (in-memory TTL) используется в backend и bot. Идентификаторы должны совпадать между сервисами:

| Сущность | Идентификатор | Пример ключа кеша |
|---|---|---|
| `User` | `tg_id` | `user_123456` |
| `Key` | `email` (не `id`!) | `key_user@example.com` |
| `Inbound` | `(server_id, inbound_id)` | `inbound_1_5` |
| `PaymentModel` | `payment_id` (не `id`!) | `payment_yoo_12345` |

## Тесты

```bash
# Backend
cd backend && pytest
cd backend && pytest tests/api/test_keys.py
cd backend && pytest tests/api/test_keys.py::test_list_keys

# Bot
cd bot && pytest
cd bot && pytest tests/models/
cd bot && pytest -k test_name
cd bot && make test          # через Makefile

# Web (unit)
cd web && pytest

# Web (E2E, требует браузер)
cd web && npx playwright test
cd web && npx playwright test --grep "auth"
```

## Линтинг

```bash
# Bot
cd bot && make lint         # ruff check
cd bot && make formatting   # ruff check --fix + ruff format
```

## Мониторинг

```bash
# Проверка состояния backend
curl http://localhost:8000/health

# Готовность (включая БД)
curl http://localhost:8000/readiness

# Метрики Prometheus
curl http://localhost:8000/metrics

# Сброс кеша вручную
curl -X POST http://localhost:8000/api/v1/admin/rebuild-cache \
  -H "X-Bot-Secret: <BOT_SECRET_KEY>"
```

## Стек технологий

- **Backend:** FastAPI, asyncpg, httpx, yookassa, APScheduler, punq, tenacity, prometheus-client
- **Bot:** aiogram 3, aiogram-dialog, httpx, punq, loguru, ruff
- **Web:** FastAPI, httpx, python-jose, asyncpg
- **База данных:** PostgreSQL 16
- **Контейнеризация и прокси:** Docker, Docker Compose, nginx
