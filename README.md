<!-- generated-by: gsd-doc-writer -->
# VPN Platform

Монорепо для VPN-сервиса с тремя компонентами: FastAPI-бэкенд (источник истины), Telegram-бот и веб-интерфейс.

## Архитектура

| Компонент | Путь | Роль | Порт |
|---|---|---|---|
| FastAPI Backend | `backend/` | Бизнес-логика, 3x-UI, YooKassa, кеш | 8000 |
| Telegram Bot | `bot/` | Диалоги, хендлеры, уведомления пользователей | — |
| Web Interface | `web/` | SPA + тонкий FastAPI-прокси поверх backend API | 8001 |

**Контракт:** Бот и веб не обращаются напрямую к БД — только через backend API. Вся бизнес-логика (ключи, платежи, тарифы), 3x-UI и YooKassa — исключительно в `backend/`.

## Требования

- Python 3.11+
- Docker и Docker Compose
- PostgreSQL 16 (запускается через Docker Compose)

## Установка и запуск

### Полный запуск через Docker Compose

```bash
git clone <repository-url>
cd vpn-platform
# Настройте .env файлы для каждого компонента (см. ниже)
docker-compose up -d
```

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

Каждый компонент требует отдельный `.env` файл.

### backend/.env

| Переменная | Описание |
|---|---|
| `DATABASE_URL` | asyncpg DSN для PostgreSQL |
| `BOT_SECRET_KEY` | Shared secret для аутентификации бота/веба |
| `TELEGRAM_BOT_TOKEN` | Токен бота (для отправки уведомлений) |
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

Все настройки через `.env`: токены бота, БД, 3x-UI, YooKassa, вебхук, тарифы, реферальные проценты.

## Аутентификация между сервисами

| Клиент | Заголовок | Описание |
|---|---|---|
| Бот → Backend | `X-Bot-Secret: <BOT_SECRET_KEY>` | Shared secret |
| Веб → Backend | `X-Bot-Secret: <BOT_SECRET_KEY>` | Shared secret |
| Веб → Пользователь | JWT в HttpOnly cookie | `access_token` + `refresh_token` |
| Админ → Backend | `X-API-Key: <ADMIN_API_KEY>` | Admin operations |

## API Backend (порт 8000)

Основные группы эндпоинтов под префиксом `/api/v1`:

- `GET|POST|DELETE /keys` — управление VPN-ключами
- `GET|POST /payments` — история и создание платежей, YooKassa webhook
- `GET /tariffs` — тарифные планы
- `GET|POST /users` — пользователи
- `GET|POST /admin` — здоровье системы, сброс кеша

Полная документация: `/docs` (Swagger UI при запущенном бэкенде).

## Тесты

```bash
# Backend
cd backend && pytest

# Bot
cd bot && pytest

# Web (unit)
cd web && pytest

# Web (E2E, требует браузер)
cd web && npx playwright test
```

## Мониторинг

```bash
# Проверка состояния backend
curl http://localhost:8000/health

# Готовность (включая БД)
curl http://localhost:8000/readiness

# Сброс кеша вручную
curl -X POST http://localhost:8000/api/v1/admin/rebuild-cache \
  -H "X-Bot-Secret: <BOT_SECRET_KEY>"
```

## Стек технологий

- **Backend:** FastAPI, asyncpg, py3xui, yookassa, APScheduler, punq
- **Bot:** aiogram 3, aiogram-dialog, asyncpg, loguru
- **Web:** FastAPI, httpx, python-jose, asyncpg
- **База данных:** PostgreSQL 16
- **Контейнеризация:** Docker, Docker Compose
