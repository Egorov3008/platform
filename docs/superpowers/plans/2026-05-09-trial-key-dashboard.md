# Trial Key Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Добавить пустое состояние дашборда и форму получения пробного ключа (когда `user.trial == 0`), зеркалируя бот-флоу.

**Architecture:** Новый `POST /api/v1/keys/trial` в бэкенде атомарно создаёт ключ и ставит `trial=1`. Веб-слой проксирует через `POST /api/v1/keys/trial` и добавляет `GET /api/v1/users/me`. Фронтенд запрашивает `user.trial` при загрузке дашборда и показывает форму только если `trial == 0`.

**Tech Stack:** FastAPI, asyncpg, asyncio, vanilla JS (ES modules), CSS custom properties

---

## Files

| File | Action |
|---|---|
| `backend/api/v1/keys.py` | Modify — add `POST /trial` |
| `backend/tests/api/test_keys.py` | Modify — add trial tests |
| `web/app/api/backend_client.py` | Modify — add `create_trial_key()` |
| `web/app/api/users.py` | Create — `GET /me` |
| `web/app/api/keys.py` | Modify — add `POST /trial` |
| `web/app/main.py` | Modify — register users router |
| `web/tests/test_keys.py` | Modify — add trial test |
| `web/tests/test_users.py` | Create — test `GET /me` |
| `web/frontend/style.css` | Modify — empty-card + trial styles |
| `web/frontend/js/pages.js` | Modify — dashboard empty state |

---

## Task 1: Backend — `POST /api/v1/keys/trial`

**Files:**
- Modify: `backend/api/v1/keys.py`
- Modify: `backend/tests/api/test_keys.py`

- [ ] **Step 1: Write failing tests**

Append to `backend/tests/api/test_keys.py`:

```python
from unittest.mock import patch, AsyncMock as _AsyncMock


def make_user(tg_id=123, trial=0):
    from unittest.mock import MagicMock
    u = MagicMock()
    u.tg_id = tg_id
    u.trial = trial
    u.server_id = 2
    return u


def make_tariff(tariff_id=10, amount=0.0):
    from unittest.mock import MagicMock
    t = MagicMock()
    t.id = tariff_id
    t.amount = amount
    t.name_tariff = "Пробный"
    return t


@pytest.mark.asyncio
async def test_create_trial_key_success(api_client, mock_service_data):
    user = make_user(trial=0)
    tariff = make_tariff()
    key = make_key(email="trial@123.vpn")

    mock_service_data.users.get_data = AsyncMock(return_value=user)
    mock_service_data.tariffs.get_data = AsyncMock(return_value=tariff)
    mock_service_data.keys.get_data = AsyncMock(return_value=key)

    with patch("api.v1.keys.build_key_services") as mock_build, \
         patch("api.v1.keys.TrialService") as mock_trial_cls:
        mock_create = AsyncMock(return_value={"email": "trial@123.vpn"})
        mock_build.return_value = (MagicMock(proces=mock_create), None, None)
        mock_trial = AsyncMock()
        mock_trial_cls.return_value.installation_trial = mock_trial

        resp = await api_client.post("/api/v1/keys/trial?tg_id=123")

    assert resp.status_code == 200
    mock_trial.assert_called_once_with(123, pytest.approx(object()), trial=1)


@pytest.mark.asyncio
async def test_create_trial_key_already_used(api_client, mock_service_data):
    user = make_user(trial=1)
    mock_service_data.users.get_data = AsyncMock(return_value=user)

    resp = await api_client.post("/api/v1/keys/trial?tg_id=123")
    assert resp.status_code == 403
    assert "Trial already used" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_create_trial_key_user_not_found(api_client, mock_service_data):
    mock_service_data.users.get_data = AsyncMock(return_value=None)

    resp = await api_client.post("/api/v1/keys/trial?tg_id=999")
    assert resp.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/claude/vpn-platform/backend && python -m pytest tests/api/test_keys.py::test_create_trial_key_success tests/api/test_keys.py::test_create_trial_key_already_used tests/api/test_keys.py::test_create_trial_key_user_not_found -v
```
Expected: FAIL — `404 Not Found` (route doesn't exist yet)

- [ ] **Step 3: Add imports to `backend/api/v1/keys.py`**

Add to the imports at the top of `backend/api/v1/keys.py` (after existing imports):

```python
from config import DEFAULT_PRICING_PLAN
from services.core.user.utils.trial import TrialService
```

- [ ] **Step 4: Add the `POST /trial` endpoint**

Append before the `@router.delete` line in `backend/api/v1/keys.py`:

```python
@router.post("/trial", response_model=KeyResponse)
async def create_trial_key(
    tg_id: int = Query(..., description="Telegram user ID"),
    _: None = Depends(verify_bot_secret),
    pool: asyncpg.Pool = Depends(get_pool),
    service_data: ServiceDataModel = Depends(get_service_data),
    cache: CacheService = Depends(get_cache),
) -> KeyResponse:
    """Create a free trial VPN key (sets user.trial = 1)"""
    user = await service_data.users.get_data(tg_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.trial != 0:
        raise HTTPException(status_code=403, detail="Trial already used")

    tariff = await service_data.tariffs.get_data(int(DEFAULT_PRICING_PLAN))
    if not tariff:
        raise HTTPException(status_code=404, detail="Trial tariff not found")

    data_service = DataService()
    create_key_svc, _, _ = build_key_services(pool, service_data, cache, data_service)

    result = await create_key_svc.proces(
        tg_id=tg_id,
        tariff=tariff,
        server_id=2,
        conn=pool,
        number_of_months=1,
    )

    if not result:
        raise HTTPException(status_code=500, detail="Failed to create trial key")

    key = await service_data.keys.get_data(result["email"])
    if not key:
        raise HTTPException(status_code=500, detail="Created key not found in database")

    await TrialService(service_data).installation_trial(tg_id, pool, trial=1)

    return KeyResponse.from_key(key)
```

**Note:** `POST /trial` must be declared before `POST /{email}/renew` to avoid route conflicts. It's appended before `@router.delete`, which is correct — `delete` comes after `create`.

Actually, double-check the file order. The routes are:
1. `GET /` — list_keys
2. `GET /{email:path}` — get_key
3. `POST /create` — create_key
4. `DELETE /{email}` — delete_key
5. `POST /{email}/renew` — renew_key

Add `POST /trial` between `POST /create` (line 94) and `DELETE /{email}` (line 134). The exact placement: add the new endpoint block right after the closing line of `create_key` (after `return KeyResponse.from_key(key)` at line 131) and before `@router.delete`.

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd /home/claude/vpn-platform/backend && python -m pytest tests/api/test_keys.py::test_create_trial_key_success tests/api/test_keys.py::test_create_trial_key_already_used tests/api/test_keys.py::test_create_trial_key_user_not_found -v
```
Expected: all 3 PASS

- [ ] **Step 6: Run full backend test suite (no regressions)**

```bash
cd /home/claude/vpn-platform/backend && python -m pytest tests/ -v --tb=short 2>&1 | tail -20
```
Expected: existing tests still pass

- [ ] **Step 7: Commit**

```bash
cd /home/claude/vpn-platform && git add backend/api/v1/keys.py backend/tests/api/test_keys.py
git commit -m "feat(backend): add POST /api/v1/keys/trial endpoint"
```

---

## Task 2: Web — `create_trial_key()` in backend client

**Files:**
- Modify: `web/app/api/backend_client.py`

- [ ] **Step 1: Add `create_trial_key()` method**

In `web/app/api/backend_client.py`, append after the `create_key` method (after line ~169):

```python
    async def create_trial_key(self) -> dict:
        """POST /api/v1/keys/trial - Create a free trial VPN key."""
        method, path = "POST", "/api/v1/keys/trial"
        try:
            await self._log_request(method, path, params=self._get_params())
            resp = await self._client.post(
                path,
                headers=self._get_headers(),
                params=self._get_params(),
            )
            resp.raise_for_status()
            data = resp.json()
            self._log_response(method, path, resp.status_code, len(str(data)))
            return data
        except Exception as e:
            self._log_error(method, path, e, resp.status_code if 'resp' in locals() else None)
            raise
```

- [ ] **Step 2: Commit**

```bash
cd /home/claude/vpn-platform && git add web/app/api/backend_client.py
git commit -m "feat(web): add create_trial_key() to WebBackendClient"
```

---

## Task 3: Web — `GET /api/v1/users/me` endpoint

**Files:**
- Create: `web/app/api/users.py`
- Create: `web/tests/test_users.py`
- Modify: `web/app/main.py`

- [ ] **Step 1: Write failing test — create `web/tests/test_users.py`**

```python
"""Tests for GET /api/v1/users/me endpoint."""

import pytest
from unittest.mock import AsyncMock
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.dependencies import get_current_user, get_backend_client
from app.core.security import create_access_token
from app.api.backend_client import WebBackendClient
from app.schemas.users import UserResponse
from datetime import datetime


def make_auth_token(tg_id=123):
    return create_access_token({"sub": "1", "tg_id": tg_id, "is_admin": False})


def make_user_response(tg_id=123, trial=0):
    return UserResponse(
        tg_id=tg_id,
        is_admin=False,
        trial=trial,
        created_at=datetime(2024, 1, 1),
    )


@pytest.fixture
async def client():
    mock_backend = AsyncMock(spec=WebBackendClient)

    async def override_backend(request=None, current_user=None):
        return mock_backend

    app.dependency_overrides[get_backend_client] = override_backend
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        c.mock_backend = mock_backend
        yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_me_returns_user(client):
    client.mock_backend.get_user = AsyncMock(return_value=make_user_response(trial=0))
    client.cookies.set("access_token", make_auth_token(tg_id=123))

    resp = await client.get("/api/v1/users/me")

    assert resp.status_code == 200
    data = resp.json()
    assert data["tg_id"] == 123
    assert data["trial"] == 0


@pytest.mark.asyncio
async def test_get_me_requires_tg_id(client):
    token = create_access_token({"sub": "1", "tg_id": None, "is_admin": False})
    client.cookies.set("access_token", token)

    resp = await client.get("/api/v1/users/me")

    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_get_me_unauthenticated(client):
    resp = await client.get("/api/v1/users/me")
    assert resp.status_code == 401
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/claude/vpn-platform/web && python -m pytest tests/test_users.py -v
```
Expected: FAIL — 404 (route doesn't exist)

- [ ] **Step 3: Create `web/app/api/users.py`**

```python
"""User info endpoint — returns current user's data from backend."""

from fastapi import APIRouter, Depends, HTTPException, status
from app.api.backend_client import WebBackendClient
from app.core.dependencies import get_backend_client, get_current_user
from app.schemas.users import UserResponse
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/me", response_model=UserResponse)
async def get_me(
    backend: WebBackendClient = Depends(get_backend_client),
    current_user: dict = Depends(get_current_user),
):
    tg_id = current_user.get("tg_id")
    if not tg_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Telegram account required",
        )
    try:
        return await backend.get_user(tg_id)
    except Exception as e:
        logger.error("GET /users/me: ошибка", extra={"error": str(e), "tg_id": tg_id})
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Backend error")
```

- [ ] **Step 4: Register router in `web/app/main.py`**

Add import at the top of the imports block in `web/app/main.py`:

```python
from app.api import auth, keys, tariffs, payments, admin, users
```

Add router registration after the existing `app.include_router` calls:

```python
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd /home/claude/vpn-platform/web && python -m pytest tests/test_users.py -v
```
Expected: all 3 PASS

- [ ] **Step 6: Commit**

```bash
cd /home/claude/vpn-platform && git add web/app/api/users.py web/app/main.py web/tests/test_users.py
git commit -m "feat(web): add GET /api/v1/users/me endpoint"
```

---

## Task 4: Web — `POST /api/v1/keys/trial` endpoint

**Files:**
- Modify: `web/app/api/keys.py`
- Modify: `web/tests/test_keys.py`

- [ ] **Step 1: Write failing test**

Append to `web/tests/test_keys.py`:

```python
@pytest.mark.asyncio
async def test_create_trial_key_success(client):
    client.mock_backend.create_trial_key = AsyncMock(return_value={
        "client_id": "trial-id",
        "email": "trial@123.vpn",
        "key": "https://sub.example.com/trial",
        "expiry_time": 9999999999000,
        "tariff_id": 10,
        "name_tariff": "Пробный",
        "amount": 0,
        "period": 30,
        "used_traffic": 0,
        "total_gb": 0,
    })
    client.cookies.set("access_token", make_auth_token(tg_id=123))

    resp = await client.post("/api/v1/keys/trial")

    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "trial@123.vpn"
    client.mock_backend.create_trial_key.assert_called_once()


@pytest.mark.asyncio
async def test_create_trial_key_requires_tg_id(client):
    token = create_access_token({"sub": "1", "tg_id": None, "is_admin": False})
    client.cookies.set("access_token", token)

    resp = await client.post("/api/v1/keys/trial")

    assert resp.status_code == 403
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/claude/vpn-platform/web && python -m pytest tests/test_keys.py::test_create_trial_key_success tests/test_keys.py::test_create_trial_key_requires_tg_id -v
```
Expected: FAIL — 404 or 405

- [ ] **Step 3: Add endpoint to `web/app/api/keys.py`**

Append after the `create_key` endpoint (after its closing `raise HTTPException` block), before the `get_key` route:

```python
@router.post("/trial", response_model=KeyResponse)
async def create_trial_key(
    backend: WebBackendClient = Depends(get_backend_client),
    current_user: dict = Depends(get_current_user),
):
    tg_id = _require_tg_id(current_user)
    logger.info("POST /keys/trial: создание пробного ключа", extra={"tg_id": tg_id})
    try:
        key_data = await backend.create_trial_key()
        logger.info("POST /keys/trial: пробный ключ создан", extra={"tg_id": tg_id, "email": key_data.get("email")})
        return KeyResponse(**key_data)
    except Exception as e:
        logger.error(
            "POST /keys/trial: ошибка",
            extra={"error": str(e), "tg_id": tg_id, "error_type": type(e).__name__},
            exc_info=True,
        )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Backend error")
```

**Important:** This route must be declared before `GET /{email:path}` to avoid the catch-all path matching "trial" as an email. In the current file, `GET /` and `POST /` come first — add `POST /trial` right after `POST /` (the `create_key` endpoint).

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /home/claude/vpn-platform/web && python -m pytest tests/test_keys.py::test_create_trial_key_success tests/test_keys.py::test_create_trial_key_requires_tg_id -v
```
Expected: PASS

- [ ] **Step 5: Run full web test suite**

```bash
cd /home/claude/vpn-platform/web && python -m pytest tests/ -v --tb=short 2>&1 | tail -20
```
Expected: all existing tests still pass

- [ ] **Step 6: Commit**

```bash
cd /home/claude/vpn-platform && git add web/app/api/keys.py web/tests/test_keys.py
git commit -m "feat(web): add POST /api/v1/keys/trial endpoint"
```

---

## Task 5: Frontend CSS — empty-card + trial block styles

**Files:**
- Modify: `web/frontend/style.css`

- [ ] **Step 1: Add styles after `.empty-state` block (around line 762)**

After the `.empty-state h3` rule in `web/frontend/style.css`, add:

```css
/* ===== Empty keys state ===== */
.empty-card {
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 32px 24px;
    text-align: center;
}
.empty-card-icon { font-size: 2.8rem; line-height: 1; margin-bottom: 10px; }
.empty-card-title { font-size: 1.05rem; font-weight: 700; margin-bottom: 6px; }
.empty-card-desc {
    font-size: 0.85rem;
    color: var(--text-secondary);
    margin-bottom: 20px;
    max-width: 320px;
    margin-left: auto;
    margin-right: auto;
}

/* ===== Trial block (inside empty-card) ===== */
.trial-block {
    background: linear-gradient(135deg, var(--primary-light) 0%, var(--surface) 100%);
    border: 1px solid var(--border-2);
    border-radius: var(--radius-sm);
    padding: 16px;
    text-align: left;
    max-width: 380px;
    margin: 0 auto;
}
.trial-block-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 10px;
}
.trial-avail-badge {
    display: inline-flex;
    align-items: center;
    gap: 3px;
    background: var(--success-bg);
    color: var(--success);
    font-size: 0.68rem;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 20px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
.trial-block-name {
    font-size: 0.9rem;
    font-weight: 700;
}
.trial-features {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
    margin-bottom: 14px;
}
.trial-feat {
    font-size: 0.78rem;
    color: var(--text-secondary);
    display: flex;
    align-items: center;
    gap: 3px;
}
.trial-feat::before { content: '✓'; color: var(--success); font-weight: 700; }
.btn-trial {
    display: block;
    width: 100%;
    padding: 11px;
    background: var(--primary);
    color: #fff;
    border: none;
    border-radius: var(--radius-sm);
    font-size: 0.875rem;
    font-weight: 700;
    text-align: center;
    cursor: pointer;
    box-shadow: 0 2px 8px rgba(13, 115, 119, 0.25);
    transition: background var(--transition), box-shadow var(--transition);
}
.btn-trial:hover { background: var(--primary-hover); box-shadow: 0 4px 12px rgba(13, 115, 119, 0.35); }
.btn-trial:disabled { opacity: 0.6; cursor: not-allowed; }
.trial-note {
    font-size: 0.7rem;
    color: var(--text-tertiary);
    text-align: center;
    margin-top: 6px;
}

/* ===== Trial badge on key cards ===== */
.key-badge.trial { background: #e8f0fe; color: #1a56db; }
[data-theme="dark"] .key-badge.trial { background: rgba(26, 86, 219, 0.15); color: #6ca0f6; }
```

- [ ] **Step 2: Commit**

```bash
cd /home/claude/vpn-platform && git add web/frontend/style.css
git commit -m "feat(web): add empty-card and trial block CSS styles"
```

---

## Task 6: Frontend JS — dashboard empty state + trial form

**Files:**
- Modify: `web/frontend/js/pages.js`

- [ ] **Step 1: Replace the parallel fetch in `Pages.dashboard()`**

In `pages.js` around line 324-328, replace:

```javascript
const [keys, tariffs] = await Promise.all([
    API.get('/keys/').catch(() => []),
    API.get('/tariffs/').catch(() => []),
]);
```

with:

```javascript
const [keys, tariffs, user] = await Promise.all([
    API.get('/keys/').catch(() => []),
    API.get('/tariffs/').catch(() => []),
    API.get('/users/me').catch(() => null),
]);
```

- [ ] **Step 2: Replace the empty-state fallback and add empty-card with trial**

Find and replace the block starting at line 334 (`if (keys && keys.length > 0)`) through the empty html fallback (line 398-403). Replace the `if (!html)` block:

```javascript
// OLD (replace this):
if (!html) {
    html = `<div style="text-align:center;padding:48px 16px;color:var(--text-muted,#888);">
        <p style="font-size:1.1em;margin-bottom:8px;">У вас пока нет VPN-ключей</p>
        <p style="font-size:.9em;">Тарифы и ключи появятся здесь после настройки сервера администратором.</p>
    </div>`;
}
```

```javascript
// NEW (replace with this):
if (!keys || keys.length === 0) {
    const trialTariff = tariffs ? tariffs.find(t => t.amount === 0) : null;
    const trialAvailable = user && user.trial === 0;

    let trialBlockHtml = '';
    if (trialAvailable) {
        const period = trialTariff ? `${trialTariff.period} дней` : '30 дней';
        const devices = trialTariff ? `${trialTariff.limit_ip} ${trialTariff.limit_ip === 1 ? 'устройство' : 'устройства'}` : '1 устройство';
        const traffic = trialTariff
            ? (trialTariff.traffic_limit >= 1024 ? `${(trialTariff.traffic_limit / 1024).toFixed(0)} ТБ` : trialTariff.traffic_limit > 0 ? `${trialTariff.traffic_limit} ГБ` : 'Безлимит')
            : 'Безлимит';

        trialBlockHtml = `
        <div class="trial-block">
            <div class="trial-block-header">
                <span class="trial-avail-badge">🎁 Бесплатно</span>
                <span class="trial-block-name">Пробный период</span>
            </div>
            <div class="trial-features">
                <span class="trial-feat">${_esc(period)}</span>
                <span class="trial-feat">${_esc(devices)}</span>
                <span class="trial-feat">${_esc(traffic)}</span>
            </div>
            <button class="btn-trial" id="btn-get-trial">Получить пробный ключ</button>
            <p class="trial-note">Доступно только один раз</p>
        </div>`;
    }

    const emptyDesc = trialAvailable
        ? 'Попробуйте VPN бесплатно — или выберите тариф ниже'
        : 'Выберите тариф ниже, чтобы подключиться к VPN';

    html = `
    <div class="section-header"><h2>Мои ключи</h2></div>
    <div class="empty-card" style="margin-bottom:24px;">
        <div class="empty-card-icon">🔑</div>
        <div class="empty-card-title">У вас нет активных ключей</div>
        <div class="empty-card-desc">${_esc(emptyDesc)}</div>
        ${trialBlockHtml}
    </div>`;
}
```

- [ ] **Step 3: Add `is_trial` badge to key cards**

In the key card rendering (around line 347-371), find the badge line:
```javascript
<span class="key-badge ${badgeClass}">${badgeText}</span>
```

Replace with:
```javascript
${k.is_trial ? '<span class="key-badge trial">Пробный</span>' : ''}
<span class="key-badge ${badgeClass}">${badgeText}</span>
```

- [ ] **Step 4: Add trial button event binding after `container.innerHTML = html`**

After the `container.innerHTML = html;` line (around line 404), add before the existing copy button binding:

```javascript
// Bind trial key button
const trialBtn = container.querySelector('#btn-get-trial');
if (trialBtn) {
    trialBtn.addEventListener('click', async () => {
        trialBtn.disabled = true;
        trialBtn.textContent = 'Создаём…';
        try {
            await API.post('/keys/trial', {});
            Toast.success('Пробный ключ создан!');
            const { Router } = window.Router ? { Router: window.Router } : await import('./router.js');
            Router.render('dashboard');
        } catch (err) {
            Toast.error(err.message || 'Ошибка при создании ключа');
            trialBtn.disabled = false;
            trialBtn.textContent = 'Получить пробный ключ';
        }
    });
}
```

- [ ] **Step 5: Commit**

```bash
cd /home/claude/vpn-platform && git add web/frontend/js/pages.js
git commit -m "feat(web): dashboard empty state and trial key form"
```

---

## Task 7: Deploy and verify

- [ ] **Step 1: Rebuild and restart containers**

```bash
cd /home/claude/vpn-platform && docker compose build backend web && docker compose up -d
```

- [ ] **Step 2: Check logs for startup errors**

```bash
docker compose logs backend web --tail=15
```
Expected: both containers show "Application startup complete"

- [ ] **Step 3: Verify trial endpoint responds**

```bash
# Should return 401/403 (not 404) — endpoint exists
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/keys/trial -X POST
```
Expected: 422 or 403 (not 404)

- [ ] **Step 4: Open browser and test**

1. Open `http://127.0.0.1:8003/#/dashboard`
2. Log in as a user with `trial == 0` → должна появиться форма пробного ключа
3. Нажать «Получить пробный ключ» → ключ появляется в списке с бейджем «Пробный»
4. Обновить страницу → форма пробного ключа исчезла (trial == 1)
5. На карточке ключа нажать «Продлить» → продление работает
