# VPN Web Backend

FastAPI-бэкенд с веб-интерфейсом для управления VPN-подписками.

## Технологии

- **Python 3.12**, **FastAPI**, **Uvicorn**
- **PostgreSQL** (asyncpg), **Pydantic v2**
- **JWT** (python-jose) в HttpOnly cookies, CSRF double-submit
- Чистый SPA-фронтенд (HTML/CSS/JS, hash-роутинг)

---

## Быстрый старт

### 1. Подготовка окружения

```bash
# Клонирование и переход в директорию
git clone <repo> && cd vpn-web-backend

# Создание виртуального окружения (если ещё нет)
python3 -m venv venv
source venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt
```

### 2. Настройка конфигурации

```bash
cp .env.example .env
# Отредактируйте .env — укажите реальные значения:
#   DATABASE_URL, SECRET_KEY, TELEGRAM_BOT_TOKEN,
#   YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY и т.д.
```

### 3. Миграция базы данных

```bash
psql "$DATABASE_URL" -f migrations/001_web_auth.sql
psql "$DATABASE_URL" -f migrations/002_login_codes.sql
```

### 4. Запуск сервера

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

После запуска доступны:

| Ресурс | URL |
|---|---|
| **Веб-интерфейс** | `http://localhost:8000/` |
| **Swagger-документация** | `http://localhost:8000/docs` |
| **Health check** | `http://localhost:8000/health` |

### 5. Docker / Podman

```bash
# Docker
docker-compose up -d

# Podman
podman-compose up -d
```

---

## Веб-интерфейс

SPA-приложение на чистом HTML/CSS/JS (без фреймворков) с hash-роутингом.

### Страницы

| Страница | Хеш | Описание |
|---|---|---|
| Вход | `#/login` | Код из Telegram-бота (8 символов) |
| Мои ключи | `#/dashboard` | Список VPN-ключей, создание/продление/удаление |
| Тарифы | `#/tariffs` | Карточки тарифов, оплата через YooKassa |
| Платежи | `#/payments` | Заглушка (бэкенд не предоставляет историю) |
| Админ-панель | `#/admin` | MRR, конверсии, управление пользователями и ключами |

### Особенности

- **Mobile-first** — адаптивный дизайн от 320px до десктопа
- **HttpOnly cookies** — токены не доступны JS, CSRF double-submit защита
- **Авто-refresh** — при 401 автоматически обновляет токен через cookie
- **Toast-уведомления** — понятные сообщения об ошибках и успехе
- **Тёмная тема** — светлая тема, шрифт Inter, мягкие тени

---

## API Endpoints

Все эндпоинты под префиксом `/api/v1`.

| Префикс | Методы | Доступ | Описание |
|---|---|---|---|
| `/auth/*` | POST | Публичные (кроме refresh) | Регистрация, логин, Telegram, refresh |
| `/keys/*` | GET, POST, DELETE | Авторизованные | CRUD VPN-ключей |
| `/tariffs/*` | GET | Публичные | Список тарифов |
| `/payments/create` | POST | Авторизованные | Создание платежа через YooKassa |
| `/payments/webhook` | POST | YooKassa | Обработка уведомлений |
| `/admin/*` | GET, PATCH, POST, DELETE | Только админ | Метрики, пользователи, ключи |

### Аутентификация

| Метод | Описание |
|---|---|
| `POST /api/v1/auth/register` | Регистрация (email + пароль, опционально tg_id) |
| `POST /api/v1/auth/login` | Вход (email + пароль) → JWT |
| `POST /api/v1/auth/telegram/request` | Запрос magic-кода в Telegram |
| `POST /api/v1/auth/telegram/verify` | Проверка кода → JWT |
| `POST /api/v1/auth/refresh` | Обновление access/refresh токенов |

---

## Структура проекта

```
├── app/
│   ├── api/           # FastAPI-роутеры (эндпоинты)
│   ├── core/          # Конфиг, БД, безопасность, зависимости
│   ├── repositories/  # Слой доступа к данным (raw SQL)
│   ├── schemas/       # Pydantic-модели
│   ├── services/      # Бизнес-логика
│   └── main.py        # Точка входа + StaticFiles (фронтенд)
├── frontend/
│   └── index.html     # SPA-фронтенд (HTML/CSS/JS)
├── migrations/        # SQL-миграции
├── tests/             # Тесты (pytest)
├── requirements.txt
├── docker-compose.yml
└── Dockerfile
```

---

## Тесты

### Backend (pytest)

```bash
# Все тесты
pytest

# Конкретный файл
pytest tests/test_auth.py
pytest tests/test_admin.py
pytest tests/test_keys.py
```

### Frontend E2E (Playwright + pytest)

171 тест в реальном браузере с парсингом DOM:

```bash
# Установка
pip install playwright pytest pytest-asyncio asyncpg bcrypt
playwright install chromium

# Все E2E тесты
pytest tests_e2e/

# Или через Playwright CLI
cd tests_e2e && npm install
npx playwright test

# Отдельные модули
pytest tests_e2e/test_auth.py           # Аутентификация (23 теста)
pytest tests_e2e/test_dashboard.py      # Dashboard CRUD (22 теста)
pytest tests_e2e/test_tariffs_payments.py # Тарифы и платежи (18 тестов)
pytest tests_e2e/test_admin.py          # Админ-панель (21 тест)
pytest tests_e2e/test_routing.py        # Навигация и роутинг (26 тестов)
pytest tests_e2e/test_ui_ux.py          # UI/UX (61 тест)

# Интерактивный режим
npx playwright test --ui

# Виден браузер
npx playwright test --headed

# По тегам
pytest -m auth       # Аутентификация
pytest -m ui         # UI тесты
pytest -m admin      # Админ-панель
pytest -m responsive # Responsive тесты
pytest -m mobile     # Мобильные тесты
```

Тесты запускаются на **5 браузерах**: Chromium, Firefox, WebKit, Mobile Chrome, Mobile Safari.

Подробнее: [tests_e2e/README.md](tests_e2e/README.md)
