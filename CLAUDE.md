# VPN Platform

Монорепо для VPN-сервиса. Три компонента:

| Компонент | Путь | Роль |
|---|---|---|
| FastAPI Backend | `backend/` | Источник истины: бизнес-логика, 3x-UI, YooKassa, кеш |
| Telegram Bot | `bot/` | UI-слой: диалоги, хендлеры, уведомления пользователей |
| Web Interface | `web/` | SPA + тонкий FastAPI-слой поверх backend API |

## Контракт

- Бот и веб **не обращаются напрямую к БД** — только через backend API
- Вся бизнес-логика (ключи, платежи, тарифы) — только в `backend/`
- YooKassa и 3x-UI — только в `backend/`
- `CacheService` (in-memory) — только в `backend/`

## Запуск всей платформы

```bash
docker-compose up -d
```

## Запуск по компонентам (разработка)

```bash
# Backend (порт 8000)
cd backend && uvicorn app.main:app --reload

# Bot
cd bot && python main.py

# Web (порт 8001)
cd web && uvicorn app.main:app --port 8001 --reload
```

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

## Аутентификация между сервисами

| Клиент | Заголовок | Описание |
|---|---|---|
| Бот → Backend | `X-Bot-Secret: <BOT_SECRET_KEY>` | Shared secret |
| Веб → Backend | JWT в HttpOnly cookie | access_token + refresh_token |
| Админ → Backend | `X-API-Key: <ADMIN_API_KEY>` | Admin operations |

## Архитектура кеша (backend/)

`CacheService` — in-memory кеш с TTL, перенесён из `Bot_3xui_vpn/services/cache/`.

**Правила идентификаторов (критично):**
- `User` → `tg_id`
- `Key` → `email` (не id!)
- `Inbound` → `(server_id, inbound_id)` (два параметра!)
- `PaymentModel` → `payment_id` (не id!)

## Текущий статус миграции

- [x] Stage 0: Monorepo setup
- [ ] Stage 1: Backend API-слой (перенос services/database/models/cache из bot/)
- [ ] Stage 2: Бот переключается на backend API
- [ ] Stage 3: Веб переключается на backend API
