# E2E тесты VPN Web Frontend

End-to-end тесты для frontend VPN Web приложения с использованием **Playwright** и **pytest**.

## Архитектура тестов

```
tests_e2e/
├── config.py              # Конфигурация: URL, селекторы, таймауты, тестовые данные
├── conftest.py            # Pytest fixtures: браузер, БД, авторизация
├── package.json           # Node.js зависимости (Playwright)
├── pages/
│   └── pages.py           # Page Object Model для всех страниц
├── utils/
│   └── helpers.py         # Утилиты: парсинг DOM, ожидания, валидация
├── test_auth.py           # Тесты аутентификации (login, register, logout)
├── test_dashboard.py      # Тесты Dashboard (CRUD ключей)
├── test_tariffs_payments.py # Тесты тарифов и платежей
├── test_admin.py          # Тесты админ-панели (метрики, пользователи, ключи)
├── test_routing.py        # Тесты навигации и роутинга
└── test_ui_ux.py          # Тесты UI/UX (responsive, модалки, тосты, a11y)
```

## Установка

```bash
# 1. Установка Python зависимостей
pip install playwright pytest pytest-asyncio asyncpg bcrypt

# 2. Установка Playwright браузеров
playwright install

# 3. (Опционально) Установка Node.js зависимостей
cd tests_e2e && npm install
```

## Запуск тестов

### Все тесты

```bash
# Запуск всех тестов
playwright test

# Запуск с UI (интерактивный режим)
playwright test --ui

# Запуск в headed режиме (виден браузер)
playwright test --headed

# Debug режим
playwright test --debug
```

### Отдельные файлы

```bash
# Тесты аутентификации
playwright test test_auth.py

# Тесты Dashboard
playwright test test_dashboard.py

# Тесты тарифов и платежей
playwright test test_tariffs_payments.py

# Тесты админ-панели
playwright test test_admin.py

# Тесты навигации
playwright test test_routing.py

# Тесты UI/UX
playwright test test_ui_ux.py
```

### По тегам (маркерам)

```bash
# Только тесты auth
pytest -m auth

# Только тесты UI
pytest -m ui

# Только тесты admin
pytest -m admin

# Responsive тесты
pytest -m responsive
```

### Конкретный тест

```bash
playwright test -k "test_successful_login"
```

## Отчеты

```bash
# Показать HTML отчет
playwright show-report

# JSON результаты
cat test-results/results.json
```

## Конфигурация

### Переменные окружения

| Переменная | Описание | По умолчанию |
|---|---|---|
| `BASE_URL` | URL приложения | `http://localhost:8000` |
| `DATABASE_URL` | URL базы данных | `postgresql://user:password@localhost:5432/vpndb` |
| `CI` | CI режим (включает retries) | `false` |

### Браузеры

Тесты запускаются на:
- Chromium (Desktop)
- Firefox (Desktop)
- WebKit (Desktop Safari)
- Mobile Chrome (Pixel 5)
- Mobile Safari (iPhone 12)

## Маркеры тестов

| Маркер | Описание |
|---|---|
| `auth` | Тесты аутентификации |
| `login` | Тесты входа |
| `register` | Тесты регистрации |
| `logout` | Тесты выхода |
| `dashboard` | Тесты Dashboard |
| `keys` | Тесты ключей |
| `create_key` | Тесты создания ключа |
| `delete_key` | Тесты удаления ключа |
| `copy_key` | Тесты копирования ключа |
| `tariffs` | Тесты тарифов |
| `payments` | Тесты платежей |
| `admin` | Тесты админ-панели |
| `metrics` | Тесты метрик |
| `users_tab` | Тесты вкладки пользователей |
| `keys_tab` | Тесты вкладки ключей |
| `routing` | Тесты роутинга |
| `guards` | Тесты guard'ов роутов |
| `navigation` | Тесты навигации |
| `mobile` | Мобильные тесты |
| `ui` | Тесты UI |
| `responsive` | Responsive тесты |
| `empty_states` | Тесты пустых состояний |
| `toasts` | Тесты уведомлений |
| `modals` | Тесты модальных окон |
| `forms` | Тесты валидации форм |
| `accessibility` | Тесты доступности |
| `visual` | Тесты визуальной консистентности |
| `integration` | Интеграционные тесты |

## Структура тестов

### Page Object Model

Каждая страница приложения имеет соответствующий Page Object класс в `pages/pages.py`:

- `BasePage` — базовый класс с общими методами
- `LoginPage` — страница входа
- `RegisterPage` — страница регистрации
- `DashboardPage` — Dashboard с ключами
- `TariffsPage` — страница тарифов
- `PaymentsPage` — страница платежей
- `AdminPage` — админ-панель
- `ModalPage` — хелпер для модальных окон
- `MobileNavigation` — хелпер мобильной навигации

### Fixtures

Основные fixtures в `conftest.py`:

- `page` — новая страница в браузере
- `mobile_page` — страница с мобильным viewport
- `db_pool` — пул соединений к БД
- `clean_database` — очищает БД перед тестом
- `registered_user` — зарегистрированный пользователь
- `admin_user` — пользователь-администратор
- `user_with_tg_link` — пользователь с привязанным Telegram
- `logged_in_user` — авторизованный пользователь
- `logged_in_admin` — авторизованный администратор

### Утилиты парсинга DOM

В `utils/helpers.py` собраны функции для:

- `parse_key_cards()` — парсинг карточек ключей
- `parse_tariff_cards()` — парсинг карточек тарифов
- `parse_admin_metrics()` — парсинг метрик админки
- `parse_admin_users_table()` — парсинг таблицы пользователей
- `parse_admin_keys_table()` — парсинг таблицы ключей
- `get_local_storage()` — чтение localStorage
- `get_access_token()` — получение JWT токена
- `validate_email_format()` — валидация email
- `validate_date_format()` — валидация даты
- `validate_currency_format()` — валидация цены

## CI/CD

Для запуска в CI:

```bash
export CI=true
playwright test
```

В CI режиме:
- Включены retries (2 попытки)
- Запрещены failed тесты
- Ограничен parallelism (1 worker)

## Отладка

### Скриншоты и видео

При падении тестов автоматически сохраняются:
- Скриншот: `test-results/failed-{test-name}.png`
- Видео: `test-results/.../*.webm`
- Трейс: `test-results/.../trace.zip`

### Просмотр трейса

```bash
playwright show-trace test-results/.../trace.zip
```

## Рекомендации

1. **Не хардкодить селекторы** — использовать `config.SELECTORS`
2. **Использовать Page Objects** — не работать с locator напрямую в тестах
3. **Писать ассерты с понятными сообщениями** — `assert x, "понятное описание"`
4. **Группировать по функциональности** — использовать маркеры
5. **Не зависеть от других тестов** — каждый тест независим
6. **Использовать fixtures** — для повторяющихся setup/teardown
