# Landing: «уже зарегистрирован» — дизайн

**Date:** 2026-06-25
**Status:** Approved (brainstorming complete, pending implementation plan)
**Scope:** backend (landing state) + web landing page

## Problem

Воронка лендинга: анонимный посетитель получает 24ч-ключ → кликает deep-link
«Продлить на неделю бесплатно» в бота → бот `/start landing_<uid>`.

Для **существующего юзера** (уже имеет аккаунт в боте) бот делает `mark-converted`:
выставляет `converted_tg_id`, но **не переносит** `tg_id` с псевдо (<0) на реальный —
24ч-ключ продолжает работать до истечения срока (см. комментарий в
`backend/api/v1/landing.py:361-366`). При этом лендинг продолжает показывать такому
юзеру обычный экран `active`/`expiring` с кнопкой «Продлить на неделю бесплатно», что
вводит в заблуждение: бесплатное продление по trial доступно только новым юзерам,
существующему нужно оформлять подписку.

Нужно: пока 24ч-ключ ещё жив, показывать такому юзеру сообщение «регистрация
временного ключа невозможна — вы уже зарегистрированы» + работающий ключ с обратным
отсчётом, а CTA «Продлить на неделю бесплатно» заменить на «Открыть бота».

## Requirements

1. **Триггер:** состояние ключа `converted_tg_id is not None` И `tg_id < 0`
   (mark-converted существующего юзера). Это же условие покрывает случай
   `already_claimed_other` (ключ привязан к чужому аккаунту) — для обоих сообщение
   «регистрация невозможна, ключ уже зарегистрирован» корректно по смыслу.
2. **Пока ключ жив:** показываем сообщение + работающий 24ч-ключ (key, обратный
   отсчёт, копирование, «Открыть в Happ») + кнопка «💬 Открыть бота» вместо
   «Продлить на неделю бесплатно». Прячем `expiring-cta` (он предлагает бесплатное
   продление, недоступное существующему юзеру).
3. **После истечения 24ч:** обычный экран `expired` БЕЗ сообщения/флага — требование
   «только пока ключ жив».
4. **Свежий ключ** (`converted_tg_id is None`) — обычный `active`/`expiring`, без
   изменений.

## Architecture

### Backend (`backend/api/v1/landing.py`)

- `LandingStateResponse` получает поле `already_registered: bool = False`.
- В `get_state` ранний `return LandingStateResponse(state="converted")` (≈ line 365)
  остаётся как есть — он ловит `converted_tg_id is not None AND tg_id > 0` (новый юзер
  забрал ключ через claim). В ветку active/expiring (после этого раннего return)
  попадают только ключи с `tg_id < 0` — либо свежие (`converted_tg_id is None`), либо
  mark-converted/already_claimed_other (`converted_tg_id is not None`).
- В финальном `return LandingStateResponse(state=state, ...)` (≈ line 381-388)
  добавить `already_registered = key_obj.converted_tg_id is not None` и
  `bot_url = f"{LANDING_BOT_LINK_PREFIX}{settings.bot_name or 'TolkoDlyaSv0ih_Bot'}"`
  (чистая ссылка бота без `?start=…` — для кнопки «Открыть бота» уже-зарегистрированным).
  Поле `bot_url` уже есть в `LandingStateResponse` (≈ line 79), для active пока не
  заполнялось. В `expired`-return (≈ line 373) флаг **не ставим** (по умолчанию `False`),
  `bot_url` там не нужен — сообщение только пока ключ жив.
- Никаких новых эндпоинтов и env-флагов.

### Web (`web/landing/`)

- `index.html`, `screen-active`: добавить баннер
  `<div id="already-registered-banner" class="info-banner" hidden>…</div>` с текстом:
  «Вы уже зарегистрированы — регистрация временного ключа невозможна. Бесплатное
  продление недоступно — оформите подписку в боте.»
- `app.js` `renderState`, ветка `active`/`expiring` (после `showScreen('active')`):
  - если `state.already_registered === true`:
    - показать `#already-registered-banner`;
    - `#open-bot` → `textContent = '💬 Открыть бота'`, `href = state.bot_url` (чистая
      ссылка бота без `?start=…`, чтобы не дёргать mark-converted повторно — хотя он
      идемпотентен, чистая ссылка чище);
    - скрыть `#expiring-cta`.
  - иначе: скрыть баннер, вернуть `#open-bot` исходный текст «⏳ Продлить на неделю
    бесплатно» и `href = state.deep_link_bot`.
- Разметка ключа/обратного отсчёта/Happ/копирования переиспользуется без изменений.

### Bot

Не трогаем. Бот уже корректно пишет существующему юзеру «✅ Вы уже зарегистрированы …
оформите подписку» (`bot/handlers/start_from_landing.py:126-130`).

## Error handling

| Случай | state | already_registered | UI |
|---|---|---|---|
| Свежий ключ, жив | active/expiring | false | обычный active |
| mark-converted, ключ жив | active/expiring | **true** | баннер + ключ + «Открыть бота» |
| already_claimed_other, ключ жив | active/expiring | **true** | то же (сообщение корректно) |
| mark-converted, ключ истёк | expired | false | обычный expired |
| claim (новый юзер) | converted | false (ранний return) | обычный converted |

## Testing

### Backend unit (`backend/tests/api/test_landing.py`, моки `service_data`)

- `test_state_already_registered_mark_converted`: ключ с `converted_tg_id=999`,
  `tg_id=-100542224`, expiry в будущем → `state` ∈ {`active`,`expiring`},
  `already_registered is True`, `key_value` присутствует (отсчёт работает).
- `test_state_fresh_key_not_already_registered`: ключ с `converted_tg_id=None`,
  expiry в будущем → `already_registered is False`.
- `test_state_expired_converted_no_flag`: ключ с `converted_tg_id=999`, `tg_id<0`,
  expiry в прошлом → `state == "expired"`, `already_registered is False`.

Использует существующие фикстуры `api_client` / `mock_service_data` и хелперы
`make_landing_key` / `_sign_cookie` из `tests/api/test_landing.py` (как тесты
test-mode/reset плана). `cache_service.keys.all` мокается на возврат ключа.

### Web

Ручной smoke (автоматизированного web-теста для лендинга нет, как и в плане
test-mode): перевести тестовый ключ в `converted_tg_id set + tg_id<0` (существующий
юзер кликает deep-link), открыть лендинг — убедиться, что баннер виден, кнопка
«Открыть бота», `expiring-cta` скрыт, отсчёт идёт; после истечения — обычный expired.

## Out of scope

- Изменение сообщений бота (уже корректны).
- Изменение expired-экрана для уже-зарегистрированных (по решению — только пока ключ жив).
- Web E2E (Playwright) для лендинга.
- Связь с планом test-mode/reset: тот добавит поле `test_mode` и эндпоинт `/reset` —
  поле `already_registered` с ним не конфликтует (независимые поля).

## Open questions

Нет. Все ключевые решения подтверждены пользователем:
- сценарий — существующий юзер после бота (mark-converted);
- экран — сообщение + работающий 24ч-ключ, кнопка «Продлить» → «Открыть бота»;
- после истечения — обычный expired, сообщение только пока ключ жив.