# Landing test-mode & session reset — Design

**Date:** 2026-06-25
**Status:** Approved (brainstorming complete, pending implementation plan)
**Scope:** backend + web landing page

## Problem

Для ручного тестирования лендинг-воронки (quick-key → 24ч-ключ → deep-link в бот →
claim) нужно прогонять сценарий многократно. Сейчас состояние сессии живёт в
подписанной куке `tg_landing_id` (90 дней), привязанной к `landing_uid` → ключу в БД,
и сброса нет: после первого «Получить ключ» `/state` всегда отдаёт `active/expiring/
expired`, вернуться к `new` можно только ручным удалением куки в DevTools.

Нужно: тестовый режим, в котором тестер одной кнопкой сбрасывает сессию лендинга —
чистит куку и удаляет текущий 24ч-ключ из БД, кеша и 3x-UI. Чистый слейт каждый прогон.

## Requirements

1. **Сброс = кука + удаление ключа** (БД + кеш + 3x-UI) по `landing_uid` из куки.
2. **Гейтинг:** кнопка видна только когда бэкенд отдаёт `state.test_mode=true`.
   `test_mode` управляется env-флагом `LANDING_TEST_MODE` (off в проде). Эндпоинт
   сброса защищён `X-Bot-Secret` (инжектит nginx), как все `/api/v1/landing/*`.
3. **Защита converted-ключа:** если ключ уже привязан к реальному `tg_id`
   (`converted_tg_id is not None`) — сброс возвращает **409** и ключ не трогает.
   Сброс работает только на анонимном 24ч-ключе до claim.
4. **Идемпотентность:** нет куки / нет ключа → 200, состояние `new`.

## Architecture

### Backend (`backend/api/v1/landing.py`)

- Новый env-флаг в `backend/config.py`:
  ```python
  landing_test_mode: bool = Field(default=False, alias="LANDING_TEST_MODE")
  ```
- `LandingStateResponse` получает поле `test_mode: bool = False`. `get_state`
  отдаёт `settings.landing_test_mode` во **всех** ветках ответа (new/active/expiring/
  expired/converted).
- Новый эндпоинт `POST /landing/reset`:
  1. Прочитать куку `tg_landing_id`, верифицировать `_verify_cookie` → `landing_uid`.
     Нет / невалидна → `200 {"ok": True, "state": "new"}`.
  2. `_get_key_by_landing_uid(service_data, pool, landing_uid)` → `key`.
     Нет ключа → `response.delete_cookie("tg_landing_id", path="/")`,
     `200 {"ok": True, "state": "new"}`.
  3. `key.converted_tg_id is not None` → `409 {"detail": "Key already claimed"}`.
  4. `build_key_services(pool, service_data, cache, DataService())` → `_, _, xui`.
     `xui.delete_client(key.email, key.inbound_id, key.client_id)`; `False` → 500.
  5. `service_data.data_service.keys.delete(pool, email=key.email)`.
  6. `service_data.cache_service.keys.delete(CacheKeyManager.key(key.email))`.
  7. `response.delete_cookie("tg_landing_id", path="/")`.
  8. `logger.info("Landing session reset", landing_uid=..., email=...)` →
     `200 {"ok": True, "state": "new"}`.

  Паттерн удаления (шаги 4-6) зеркалирует `DELETE /api/v1/keys/{email}`
  (`api/v1/keys.py:191-226`) и admin-эндпоинты.

### Web (`web/landing/`)

- `index.html`: кнопка `<button id="reset-session" hidden>Сбросить сессию (тест)</button>`
  на экранах `active` / `expiring` / `expired` (на `new` не нужна).
- `app.js`:
  - В `renderState(state)`: `document.getElementById('reset-session').hidden =
    !(state.test_mode === true)`.
  - Обработчик клика → `fetch('/api/v1/landing/reset', {method:'POST',
    credentials:'include'})` → `loadState()`.

### Config / nginx

- nginx **не трогаем** — `X-Bot-Secret` уже инжектится на `/api/v1/landing/*`
  (`nginx/default.conf.template`).
- В `backend/.env` добавить `LANDING_TEST_MODE=0` (off по умолчанию).

## Error handling

| Случай | HTTP | Поведение |
|---|---|---|
| Нет/невалидная кука | 200 | `{"ok": true, "state": "new"}` |
| Кука есть, ключа в БД нет | 200 | чистим куку, `state: "new"` |
| Ключ уже converted | **409** | `{"detail": "Key already claimed"}`, ничего не удаляем |
| 3x-UI не удалил | 500 | `{"detail": "Failed to delete key from server"}` |
| Успех | 200 | `{"ok": true, "state": "new"}` + кука удалена |

## Testing

### Backend unit (`tests/api/test_landing.py`, моки `service_data` + `xui`)

- `test_reset_anonymous_key_deletes_everywhere`: кука валидна, ключ без
  `converted_tg_id` → 200, вызваны `xui.delete_client`, `data_service.keys.delete`,
  `cache_service.keys.delete`, кука удалена.
- `test_reset_converted_key_refused_409`: `converted_tg_id` выставлен → 409, ни один
  delete не вызван.
- `test_reset_no_cookie_idempotent`: нет куки → 200 `state: "new"`, ничего не вызывается.
- `test_reset_no_key_idempotent`: кука есть, ключ не найден → 200, кука удалена.
- `test_state_exposes_test_mode`: `settings.landing_test_mode=True` →
  `state["test_mode"] is True`; `False` → `False` (во всех ветках состояний).

`build_key_services` патчим через `app.factories` (monkeypatch на модуль, где
импортируется, как делают существующие landing-тесты).

### Backend integration (опц., против ephemeral Postgres)

Переиспользовать шаблон `tests/integration/test_keys_update_real_db.py`:
поднять ephemeral postgres, сеем landing-ключ (pseudo_tg_id, landing_uid), `POST
/landing/reset` (с подписанной кукой), assert строка удалена, кука очищена. Пропускается
без `TEST_DATABASE_URL`. 3x-UI `delete_client` мокается.

## Out of scope

- Сброс trial-флага / `users.server_id` / удаления юзера, зарегистрированного ботом
  при claim — не делаем. Сброс касается только landing-ключа и куки.
- Web E2E (Playwright) для лендинга — отдельная работа (см. коммит-историю: лендинг
  E2E не покрыт, и claim из SPA не дёргается).

## Open questions

Нет. Все 3 ключевых решения подтверждены пользователем:
глубина сброса (кука+ключ), гейтинг (кнопка+env-флаг), поведение с converted (409).