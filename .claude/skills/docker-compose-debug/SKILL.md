---
name: docker-compose-debug
description: "Диагностика docker-compose логов для монорепо VPN 3x-UI (backend/bot/web/postgres). Быстрое определение: падений бота, ошибок DI, проблем Telegram API, состояния backend/web и Postgres."
---
# Docker Compose Debug — Диагностика логов VPN-проекта

Скилл для быстрого разбора `docker compose logs` в монорепо с сервисами **backend**, **bot**, **web**, **postgres**.

## When to Apply

Используй при запросах вида:
- «проверь логи» / «что в docker compose» / «почему падает бот»
- «bot restarting» / «backend не отвечает» / «ошибка Unauthorized»
- любой запрос, связанный с диагностикой состояния контейнеров

## Быстрый старт

```bash
# Общий статус контейнеров
docker compose ps

# Логи всех сервисов (последние 100 строк)
docker compose logs --tail=100

# Логи конкретного сервиса с таймштампами
docker compose logs --tail=50 -t backend
docker compose logs --tail=50 -t bot
docker compose logs --tail=50 -t web
docker compose logs --tail=20 -t postgres

# Логи в реальном времени (фильтр по ошибкам)
docker compose logs -f | grep -E "ERROR|CRITICAL|Unauthorized|Traceback"
```

## Чек-лист диагностики по сервисам

### 1. Postgres

**Норма:**
```
LOG:  database system is ready to accept connections
```

**Проблемы:**
- `Skipping initialization` + нет `ready to accept connections` → БД не поднялась, проверь `DATABASE_URL` и права на volume.
- `FATAL:  password authentication failed` → неверные креды в `.env`.

### 2. Backend

**Норма:**
```
SUCCESS | Пул соединений с БД успешно создан
INFO    | Загрузка кэша завершена
INFO    | Scheduler started
Uvicorn running on http://0.0.0.0:8000
```

**Проблемы:**
- `ConnectionRefusedError` к БД → postgres ещё инициализируется или `DATABASE_URL` неверен.
- `ImportError` / `ModuleNotFoundError` → сломан импорт после рефакторинга.
- `Error in ASGI Framework` → FastAPI падает при старте (вероятно, ошибка в lifespan или зависимостях).

### 3. Web

**Норма:**
```
INFO | Backend HTTP client initialized: http://backend:8000
INFO | Uvicorn running on https://0.0.0.0:8443
```

**Проблемы:**
- `Connection refused` к backend → backend не поднялся или нет сети между контейнерами.
- `ModuleNotFoundError` / `Jinja2` ошибки → проблемы в шаблонах или импортах web-слоя.

### 4. Bot (самый хрупкий сервис)

#### 4.1 Ошибка DI / `TypeError: Can't instantiate abstract class`

**Сигнатура:**
```
TypeError: Can't instantiate abstract class CreateFerstKeyScenario with abstract method get_data
```

**Что значит:**
Класс наследует от `ABC` и не реализует все `@abstractmethod`.

**Где чинить:**
- Посмотри файл сценария: `bot/services/scenarios/<name>.py`
- Сравни с родителем `ScenarioFactory` (`bot/services/scenarios/factory_scenario.py`)
- Либо добавь недостающий метод в наследник, либо убери `@abstractmethod` у родителя, если он больше не нужен.

**Какие окна ломаются чаще всего:**
- `MainMenu:main` (клавиатура профиля)
- `Instruction:android/iphone/windows/linux` (клавиатуры инструкций)

#### 4.2 Telegram API — `Unauthorized`

**Варианты ошибок:**
```
TelegramUnauthorizedError: Unauthorized: SESSION_REVOKED
TelegramUnauthorizedError: Unauthorized
```

**Что значит:** токен бота невалиден (отозван через @BotFather, сброшен, или используется на другом сервере).

**Что делать:**
1. Проверь `TELEGRAM_BOT_TOKEN` в `.env` бота.
2. Убедись, что токен не отозван в @BotFather.
3. Если это staging/dev — убедись, что токен не используется одновременно в проде (Telegram блокирует duplicate polling).

#### 4.3 `RuntimeError: Router is already attached`

**Сигнатура:**
```
RuntimeError: Router is already attached to <Dispatcher '0x...'>
```

**Что значит:** при перезапуске (fallback/retry loop) старый `Dispatcher` не очищен, а код пытается повторно включить роутеры.

**Где чинить:**
- `bot/main.py` — в цикле рестарта нужно пересоздавать `Dispatcher()` заново или отключать роутеры от старого.

#### 4.4 Циклический рестарт

**Сигнатуры:**
```
CRITICAL | Достигнуто максимальное количество перезапусков, завершение работы
bot-1 exited with code 0 (restarting)
```

**Что значит:** бот упал 5 раз подряд, Docker перезапускает контейнер. Получается бесконечный restart loop.

**Что делать:**
- Чини первопричину (DI или Telegram токен).
- Временно можно остановить бота: `docker compose stop bot`.

## Шаблон ответа пользователю

При анализе логов структурируй ответ так:

1. **Сводка по сервисам** — таблица зелёный/красный статус.
2. **Главная проблема** — одна или две ошибки, которые ломают работу.
3. **Корневые причины** — что именно сломано (код / токен / сеть / БД).
4. **Где чинить** — конкретные файлы и строки (если видно из логов).
5. **Быстрые команды** — что ввести, чтобы увидеть больше деталей.

## Полезные команды

```bash
# Проверить healthcheck backend
curl -s http://localhost:8000/health || echo "Backend не отвечает"

# Посмотреть env бота (без секретов)
docker compose exec bot env | grep -E "^(SERVICE|ENV|DEBUG)"

# Зайти в контейнер бота для отладки
docker compose exec bot sh
python -c "from services.scenarios.create_first_key_scenario import CreateFerstKeyScenario; print('OK')"

# Пересобрать только бота
docker compose up -d --build bot

# Очистить все логи и перезапустить
docker compose down && docker compose up -d
```
