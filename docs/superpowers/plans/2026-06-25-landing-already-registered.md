# Landing «уже зарегистрирован» — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Показывать существующему (уже зарегистрированному) юзеру на лендинге, пока его 24ч-ключ жив, сообщение «регистрация временного ключа невозможна — вы уже зарегистрированы» + работающий ключ с обратным отсчётом, заменив CTA «Продлить на неделю бесплатно» на «Открыть бота».

**Architecture:** Бэкенд отдаёт флаг `already_registered` и `bot_url` в `GET /landing/state` для ветки active/expiring (триггер: `converted_tg_id is not None` И `tg_id < 0` — mark-converted / already_claimed_other). Ветка `expired` флаг не получает (сообщение только пока ключ жив). Ванильный JS на active/expiring при флаге показывает баннер, меняет кнопку, скрывает `expiring-cta`.

**Tech Stack:** FastAPI, asyncpg, pydantic, vanilla JS landing, pytest + httpx ASGITransport.

## Global Constraints

- Ключ идентифицируется по `email`. `LandingStateResponse` — в `backend/api/v1/landing.py`.
- Роутер `/landing` уже имеет `dependencies=[Depends(verify_bot_secret)]` — новых эндпоинтов нет.
- Тесты: `asyncio_mode=auto`. Фикстуры `api_client` и `mock_service_data` — в `backend/tests/api/conftest.py`. Хелперы `make_landing_key` / `_sign_cookie` / `_mock_cache` / `_override_cache` — в `backend/tests/api/test_landing.py`.
- В тестах кеш мокается через `mock_service_data.cache_service.keys.all = AsyncMock(return_value=[key])` (именно так `_get_key_by_landing_uid` находит ключ).
- Поле `bot_url` уже существует в `LandingStateResponse` (`Optional[str] = None`), для active пока не заполнялось.
- `settings.bot_name` — имя бота (default `"VPNBot"`); `LANDING_BOT_LINK_PREFIX = "https://t.me/"` — константа модуля `landing.py`.
- Коммиты на текущей ветке `refactor/remove-inbound`, сообщения заканчиваются `Co-Authored-By: Claude <noreply@anthropic.com>`.
- Не трогаем: бот (`bot/handlers/start_from_landing.py` уже корректен), expired-экран, E2E Playwright.

---

## File Structure

| File | Responsibility |
|---|---|
| `backend/api/v1/landing.py` | + `already_registered` поле; + `already_registered`/`bot_url` в `get_state` active/expiring-ветке |
| `backend/tests/api/test_landing.py` | + 3 unit-теста флага `already_registered` |
| `web/landing/index.html` | + баннер `#already-registered-banner` в `screen-active` |
| `web/landing/style.css` | + стиль `.info-banner` |
| `web/landing/app.js` | + флаг `alreadyRegistered` + ветка в `renderState` + учёт в `tick` |

---

## Task 1: Backend — флаг `already_registered` + `bot_url` в state

**Files:**
- Modify: `backend/api/v1/landing.py` (`LandingStateResponse` ≈ line 71-79; `get_state` ≈ line 365-388)
- Test: `backend/tests/api/test_landing.py` (append after `test_state_active_after_mark_converted_only`, ≈ line 470)

**Interfaces:**
- Produces: `LandingStateResponse.already_registered: bool` и `LandingStateResponse.bot_url: Optional[str]` (поле `bot_url` уже есть в модели) заполняются в active/expiring-ветке `get_state`. В `expired`/`converted`/`new`-ветках `already_registered` остаётся `False` (default).

- [ ] **Step 1: Write failing tests**

Append to `backend/tests/api/test_landing.py` (после `test_state_active_after_mark_converted_only`):

```python
@pytest.mark.asyncio
async def test_state_already_registered_after_mark_converted(api_client, mock_service_data):
    """mark-converted (converted_tg_id set, tg_id<0), ключ жив → already_registered=True + bot_url."""
    from api.v1.landing import _sign_cookie

    landing_uid = "ar_state"
    key = make_landing_key(email="ar_state@anon", landing_uid=landing_uid)
    key.converted_tg_id = 999  # mark-converted, tg_id остался псевдо (<0)
    mock_service_data.cache_service.keys.all = AsyncMock(return_value=[key])

    cookie = _sign_cookie(landing_uid)
    resp = await api_client.get(
        "/api/v1/landing/state", cookies={"tg_landing_id": cookie}
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["state"] in ("active", "expiring")
    assert data["already_registered"] is True
    assert data["key_value"] == "vless://test@example.com"
    assert data["bot_url"].startswith("https://t.me/")
    assert "start=landing_" not in data["bot_url"]


@pytest.mark.asyncio
async def test_state_fresh_key_not_already_registered(api_client, mock_service_data):
    """Свежий ключ (converted_tg_id=None), жив → already_registered=False, bot_url есть."""
    from api.v1.landing import _sign_cookie

    landing_uid = "fresh_state"
    key = make_landing_key(email="fresh_state@anon", landing_uid=landing_uid)
    # converted_tg_id не выставлен
    mock_service_data.cache_service.keys.all = AsyncMock(return_value=[key])

    cookie = _sign_cookie(landing_uid)
    resp = await api_client.get(
        "/api/v1/landing/state", cookies={"tg_landing_id": cookie}
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["state"] in ("active", "expiring")
    assert data["already_registered"] is False
    assert data["bot_url"].startswith("https://t.me/")


@pytest.mark.asyncio
async def test_state_expired_converted_no_already_registered(api_client, mock_service_data):
    """Истёкший ключ с converted_tg_id (tg_id<0) → expired, already_registered=False."""
    from api.v1.landing import _sign_cookie
    from models import Key

    landing_uid = "ar_exp"
    key = Key(
        tg_id=-999,
        client_id="uuid-are",
        email="ar_exp@anon",
        expiry_time=int((time.time() - 3600) * 1000),  # 1ч назад — истёк
        key="vless://ar",
        inbound_id=13,
        limit_ip=1,
        landing_uid=landing_uid,
        converted_tg_id=999,
    )
    mock_service_data.cache_service.keys.all = AsyncMock(return_value=[key])

    cookie = _sign_cookie(landing_uid)
    resp = await api_client.get(
        "/api/v1/landing/state", cookies={"tg_landing_id": cookie}
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["state"] == "expired"
    assert data["already_registered"] is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && source .venv/bin/activate && pytest tests/api/test_landing.py -k already_registered -v`
Expected: FAIL — `KeyError: 'already_registered'` (поля нет в ответе) для первых двух тестов; третий может упасть на `KeyError` тоже.

- [ ] **Step 3: Add `already_registered` field to response model**

In `backend/api/v1/landing.py`, в `LandingStateResponse` (≈ line 71-79) добавить поле `already_registered`:

```python
class LandingStateResponse(BaseModel):
    """Ответ на GET /landing/state"""
    state: str  # "new" | "active" | "expiring" | "expired" | "converted"
    key_value: Optional[str] = None
    expires_at_ms: Optional[int] = None
    remaining_seconds: Optional[int] = None
    deep_link_happ: Optional[str] = None
    deep_link_bot: Optional[str] = None
    bot_url: Optional[str] = None
    already_registered: bool = False
```

- [ ] **Step 4: Populate `already_registered` + `bot_url` in active/expiring branch**

In `get_state` (≈ line 365-388), заменить финальный блок (от строки `now_ms = ...` до финального `return`) на:

```python
    now_ms = int(time.time() * 1000)
    expiry_ms = int(key_obj.expiry_time or 0)

    # Определяем состояние
    if expiry_ms <= now_ms:
        return LandingStateResponse(state="expired")

    remaining_seconds = (expiry_ms - now_ms) // 1000

    deep_link_happ, deep_link_bot = _build_deep_links(key_obj.key, landing_uid)
    bot_url = f"{LANDING_BOT_LINK_PREFIX}{settings.bot_name or 'TolkoDlyaSv0ih_Bot'}"

    state = "expiring" if remaining_seconds < EXPIRING_THRESHOLD_HOURS * 3600 else "active"

    # already_registered: mark-converted (существующий юзер) или already_claimed_other
    # — converted_tg_id выставлен, но tg_id остался псевдо (<0). 24ч-ключ живёт,
    # но бесплатное продление по claim недоступно → фронт показывает баннер.
    already_registered = key_obj.converted_tg_id is not None

    return LandingStateResponse(
        state=state,
        key_value=key_obj.key,
        expires_at_ms=expiry_ms,
        remaining_seconds=remaining_seconds,
        deep_link_happ=deep_link_happ,
        deep_link_bot=deep_link_bot,
        bot_url=bot_url,
        already_registered=already_registered,
    )
```

Ранний `return LandingStateResponse(state="converted")` (≈ line 365) и ветка `expired` НЕ меняются — `already_registered` там остаётся `False` (default), `bot_url` — `None`.

- [ ] **Step 5: Run tests to verify pass**

Run: `pytest tests/api/test_landing.py -k already_registered -v`
Expected: 3 passed.

- [ ] **Step 6: Run full landing suite (regression)**

Run: `pytest tests/api/test_landing.py -q`
Expected: all passed (включая существующие `test_state_active_with_valid_cookie`, `test_state_active_after_mark_converted_only`, `test_state_converted_after_claim` — поле с default не ломает старые ассерты).

- [ ] **Step 7: Commit**

```bash
cd /home/admin/platform
git add backend/api/v1/landing.py backend/tests/api/test_landing.py
git commit -m "feat(backend): state.already_registered flag + bot_url for landing

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 2: Web — баннер «уже зарегистрированы» + wiring

**Files:**
- Modify: `web/landing/index.html` (`screen-active`, ≈ line 128-175)
- Modify: `web/landing/style.css` (append `.info-banner`)
- Modify: `web/landing/app.js` (`renderState` active/expiring branch ≈ line 69-76; countdown module flag + `tick` ≈ line 92-119)

**Interfaces:**
- Consumes: `state.already_registered` и `state.bot_url` из Task 1.
- Produces: на active/expiring при `already_registered` — баннер `#already-registered-banner`, кнопка `#open-bot` с текстом «💬 Открыть бота» и `href = state.bot_url`, скрытый `#expiring-cta`. Иначе — обычный active (кнопка «⏳ Продлить на неделю бесплатно», `href = state.deep_link_bot`).

> Автоматизированного web-теста для лендинга нет (как и в плане test-mode) — Task 2 проверяется ручным smoke (Step 5).

- [ ] **Step 1: Add banner markup to `screen-active`**

In `web/landing/index.html`, внутри `<section id="screen-active" class="screen" hidden>` сразу после закрывающего `</div>` блока `<div class="hero">…</div>` (≈ line 135), добавить:

```html
            <div id="already-registered-banner" class="info-banner" hidden>
                <p><strong>ℹ️ Вы уже зарегистрированы.</strong></p>
                <p>Регистрация временного ключа невозможна. Бесплатное продление недоступно — оформите подписку в Telegram-боте.</p>
            </div>
```

- [ ] **Step 2: Add `.info-banner` style**

In `web/landing/style.css`, append (после `.cta-box strong { … }` блока, ≈ line 483):

```css
/* ----- Info banner (уже зарегистрирован) ----- */

.info-banner {
    background: linear-gradient(135deg, rgba(59, 130, 246, 0.14) 0%, rgba(99, 102, 241, 0.06) 100%);
    border: 1px solid rgba(59, 130, 246, 0.45);
    border-radius: var(--radius);
    padding: 22px;
    margin: 24px 0;
    text-align: center;
    backdrop-filter: blur(8px);
}

.info-banner p {
    margin-bottom: 10px;
    font-size: 15px;
}

.info-banner strong {
    color: #60a5fa;
}
```

- [ ] **Step 3: Wire `renderState` + countdown flag in `app.js`**

In `web/landing/app.js`:

3a. Добавить модульный флаг рядом с `countdownTimer` (≈ line 94):

```javascript
let countdownTimer = null;
let alreadyRegistered = false;  // управляет скрытием expiring-cta для уже-зарегистрированных
```

3b. Заменить ветку `case 'active': case 'expiring':` в `renderState` (≈ line 69-76) на:

```javascript
        case 'active':
        case 'expiring':
            showScreen('active');
            document.getElementById('key-text').textContent = state.key_value || '';
            document.getElementById('open-happ').href = state.deep_link_happ || '#';

            const openBot = document.getElementById('open-bot');
            const banner = document.getElementById('already-registered-banner');
            alreadyRegistered = state.already_registered === true;
            if (alreadyRegistered) {
                banner.hidden = false;
                openBot.textContent = '💬 Открыть бота';
                openBot.href = state.bot_url || '#';
            } else {
                banner.hidden = true;
                openBot.innerHTML = '<span>⏳</span> Продлить на неделю бесплатно';
                openBot.href = state.deep_link_bot || '#';
            }

            startCountdown(state.expires_at_ms);
            break;
```

3c. В `startCountdown` (≈ line 102-115), заменить строку `expiringCta.hidden = !isExpiring;` на:

```javascript
        const isExpiring = remaining > 0 && remaining < EXPIRING_THRESHOLD_HOURS * 3600 * 1000;
        // Уже-зарегистрированным не показываем CTA «продлите бесплатно»
        expiringCta.hidden = alreadyRegistered ? true : !isExpiring;
```

(Остальное в `tick` без изменений — `clearInterval`, перезагрузка state при `remaining <= 0`.)

- [ ] **Step 4: Sanity-check JS syntax**

Run: `cd /home/admin/platform && node --check web/landing/app.js`
Expected: no output (syntax OK).

- [ ] **Step 5: Manual smoke check (no automated web test)**

```bash
cd /home/admin/platform
docker compose up -d --build backend nginx
```

Сценарий в браузере на `https://tolko-dlya-svoih.ru:8443/landing/`:
1. Новым инкогнито-окном: «Получить ключ» → active-экран (кнопка «⏳ Продлить на неделю бесплатно», баннера нет) — свежий ключ, `already_registered=false`.
2. Существующий юзер (имеющий аккаунт в боте) кликает deep-link «Продлить на неделю бесплатно» в бота → бот пишет «✅ Вы уже зарегистрированы» (mark-converted).
3. Возврат на лендинг (или ждать ≤5 мин опроса) → на active-экране появляется синий баннер «ℹ️ Вы уже зарегистрированы», кнопка «💬 Открыть бота» (без `?start=…`), `expiring-cta` скрыт, обратный отсчёт идёт, ключ и «Открыть в Happ» на месте.
4. Дождаться истечения 24ч (или сдвинуть expiry в БД: `UPDATE keys SET expiry_time = (extract(epoch from now())*1000 - 1)::bigint WHERE landing_uid='<uid>'`) → `loadState` → обычный `expired`-экран БЕЗ баннера.
5. Свежий ключ повторно → active без баннера (флаг сбросился).

- [ ] **Step 6: Commit**

```bash
cd /home/admin/platform
git add web/landing/index.html web/landing/style.css web/landing/app.js
git commit -m "feat(web): landing already-registered banner + bot CTA swap

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Self-Review notes

- Spec coverage: Task 1 → флаг `already_registered` + `bot_url` (active/expiring, expired без флага); Task 2 → баннер + замена кнопки + скрытие `expiring-cta` + учёт в `tick`. Триггер `converted_tg_id is not None AND tg_id < 0` (через ранний `converted`-return для `tg_id > 0` и fall-through для `tg_id < 0`) — покрыт тестами `test_state_already_registered_after_mark_converted` (mark-converted) и `test_state_expired_converted_no_already_registered` (expired не флажит).
- `already_registered` / `bot_url` / `alreadyRegistered` — имена согласованы между бэкенд-ответом и фронтом.
- `bot_url` собирается через `LANDING_BOT_LINK_PREFIX` + `settings.bot_name` — согласовано с `_build_deep_links` (та же формула).
- `alreadyRegistered` модульный флаг учавствует в `tick`, чтобы `expiring-cta` не всплывал повторно для уже-зарегистрированных — без этого `startCountdown` перезаписал бы `hidden` через секунду.
- Совместимость с планом test-mode/reset: тот добавит `test_mode` поле и `/reset` эндпоинт — независимые поля, конфликтов нет.