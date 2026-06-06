# Post-mortem: bot restart-storm 2026-05-31

**Date:** 2026-05-31 08:24 – 11:20 MSK
**Component:** `bot/main.py` (aiogram 3 polling loop)
**Severity:** Medium — функциональность не страдала, но 2.5 часа логов забиты retry-loop'ом и плодились orphan-процессы
**Status:** Documented; **fix deliberately deferred** (variant A or B carries design risk — see "Why no fix yet")

## Symptom

Лог-файл `bot/logs/application.2026-05-31_08-24-24_188386.log` содержит 5518 строк, из них:

- **179 раз** `TelegramConflictError: terminated by other getUpdates request; make sure that only one bot instance is running`
- **многократно** `CRITICAL Критическая ошибка в главном цикле ... RuntimeError: Router is already attached to <Dispatcher '0x...'>`
- `restart_attempt: 2..5, max_attempts: 5` — restart-loop отрабатывает полный лимит

Пользователь 552810834 несколько раз получал HTTP 500 при `/start` (auto-register → backend 500), 404 на `/api/v1/admin/users/<tg_id>` (это впоследствии починено bigint-фиксом в коммите `e782937`).

## Root cause

`bot/main.py:227-322` (current code) реализует retry-loop в `async def main()`:

```python
max_restart_attempts = 5
restart_count = 0

while restart_count < max_restart_attempts:
    try:
        await asyncio.wait_for(on_startup(), timeout=60.0)
        await setup_middlewares()
        dp.include_router(router)               # ← (1) router attached to dp
        dp.include_router(subscription_router)
        dialog_router = await setup_dialog_router()
        dp.include_router(dialog_router)
        ...
        await dp.start_polling(bot)             # ← (2) long-poll starts
        break
    except Exception as e:                      # ← (3) polling crashes
        restart_count += 1
        ...
        await asyncio.sleep(10)
        continue                                 # ← (4) loop re-enters at (1)
```

`dp` и `router` определены в `bot/bot_project.py:15` как **module-level singletons**:

```python
bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(bot=bot, storage=storage)
```

Когда polling падает с любой ошибкой (сетевой сбой, таймаут, etc.), `continue` возвращает нас к строке (1), но `router` уже имеет `parent_router = dp` — это sticky reference. Попытка `dp.include_router(router)` повторно бросает:

```
RuntimeError: Router is already attached to <Dispatcher '0x7f510adaed90'>
```

Aiogram ловит это в `except Exception`, и за 10 секунд мы получаем 5 неудачных рестартов, каждый из которых **создаёт новый bot instance в памяти** (из-за того, что on_startup переинициализирует контейнер), и все они одновременно пытаются делать `getUpdates` → Telegram отвечает 409 → 179 строк conflict-error в логе.

## Что происходит с zombie-процессами

PID 3768903, 3771980 (которые мы наблюдали в Phase A диагностике) — это **orphans от retry-loop'а**: parent watchdog завершил цикл, а spawned getUpdates-sessions остались висеть как `S`-state (sleeping interruptible) с cwd, указывающим на удалённую директорию. Они безвредны (не держат порт 8000), но мозолят глаза в `ps`.

## Why no fix yet

Рассматривались варианты:

| Variant | Plan | Verdict |
|---|---|---|
| **A** — убрать retry-loop, `sys.exit(1)` на unhandled exception; контейнер перезапускает процесс | `main.py:303-322` | ✅ Стандартная практика для long-poll сервисов; минимально инвазивно; контейнер уже supervised. Требует проверки: `restart: always` в `docker-compose.yml`? |
| **B** — пересоздавать `dp` + все router'ы перед retry | `main.py:227-322` + `bot_project.py:15` | ❌ **Tested and rejected**: aiogram 3 router'ы хранят sticky `parent_router`. Свежий `Dispatcher` не помогает — нужно пересоздавать и `router` (см. `tests/test_main_retry_loop.py::test_router_remains_attached_after_parent_swap`). Это требует переноса `dp`/`router` создания в `main()`, что инвазивно. |
| **C** — ловить `RuntimeError: Router is already attached` явно и `sys.exit(1)` | `main.py:303-322` (новый except clause) | ⚠️ Не покрывает другие RuntimeError'ы; менее чисто чем A |

**Принятое решение (2026-06-06):** документируем root cause, откладываем фикс. Аргументы:
1. С 2026-06-01 бот стабилен (Up 2 days, никаких конфликтов в логах)
2. Bug не триггерится сам по себе — нужен polling crash как первопричина
3. Реальный источник polling crash'ей в мае 31 — не установлен (он мог быть связан с backend 500/404, которые мы починили в коммите `e782937`)
4. Любой из вариантов фикса требует тщательного тестирования в dev-среде; риск регрессии > выгода в моменте

## Регрессионный тест

`bot/tests/test_main_retry_loop.py` — два теста, которые доказывают неприменимость варианта B и фиксируют контракт:

- `test_double_include_router_raises` — воспроизводит `RuntimeError: Router is already attached` при повторном `include_router`
- `test_router_remains_attached_after_parent_swap` — доказывает, что `Router.parent_router` — sticky reference; создание нового `Dispatcher` не решает проблему

Если в будущем кто-то решит внедрить variant B, оба теста скажут «нет».

## Что мониторить, чтобы триггернуть фикс

Добавить алерт (или просто обращать внимание в логах) на:
- `CRITICAL ... Критическая ошибка в главном цикле ... Router is already attached` — **один раз уже root cause**
- `TelegramConflictError` подряд ≥ 3 раз — начало шторма
- `restart_attempt: 5` — restart-loop исчерпал лимит

Когда любой из этих маркеров появится в production → реализовать variant A.

## Связанные коммиты

- `ffb881c` — fix(notifications): основной фикс, который привёл к стабильности
- `e782937` — fix(backend): bigint-типы, могли вызывать HTTP 500/404, провоцировавшие bot polling crashes в оригинальном инциденте
- `b4a3fbf` — test(bot): regression-тест, фиксирующий контракт
