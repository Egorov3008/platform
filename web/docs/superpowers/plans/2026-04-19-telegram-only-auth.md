# Telegram-Only Authentication Flow — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace email/password and magic-link auth with a single Telegram-bot-driven code login backed by HttpOnly cookie sessions.

**Architecture:** The Telegram bot calls a new `POST /api/v1/bot/auth/generate-code` endpoint (secret-authenticated) to create a short 8-char alphanumeric code stored in a new `login_codes` table. The user enters the code on the website; the backend consumes it atomically, creates or finds a `web_users` row, and sets HttpOnly JWT cookies (`access_token`, `refresh_token`) plus a JS-readable `csrf_token` cookie. A new CSRF middleware validates `X-CSRF-Token` header == `csrf_token` cookie on all mutations except auth and bot endpoints.

**Tech Stack:** FastAPI, asyncpg, python-jose, passlib, pydantic-settings, starlette middleware, vanilla JS (frontend)

---

## File Map

| Action | File | Responsibility |
|--------|------|---------------|
| Create | `migrations/002_login_codes.sql` | Add `login_codes` table, drop `magic_tokens` |
| Modify | `app/core/config.py` | Add `bot_secret_key`, `login_code_ttl_hours`, `telegram_bot_username`, `csrf_enabled` |
| Modify | `tests/conftest.py` | Add autouse fixture to disable CSRF in tests |
| Modify | `app/core/security.py` | Add `generate_login_code`, `set_auth_cookies`, `clear_auth_cookies` |
| Create | `app/repositories/login_codes.py` | `LoginCodesRepo.create()` and `.consume()` |
| Modify | `app/core/dependencies.py` | `get_current_user` reads from `access_token` cookie instead of Bearer header |
| Create | `app/core/csrf.py` | `CSRFMiddleware` — double-submit cookie pattern |
| Modify | `app/main.py` | Register CSRF middleware + bot router |
| Modify | `app/schemas/auth.py` | Remove old schemas, add `LoginCodeRequest`, `UserInfoResponse`, `GenerateCodeRequest/Response` |
| Modify | `app/services/auth.py` | Replace all auth functions with `login_with_code` + `refresh_tokens_from_cookie` |
| Modify | `app/api/auth.py` | New endpoints: login, me, logout, refresh, config |
| Create | `app/api/bot.py` | `POST /bot/auth/generate-code` |
| Modify | `frontend/index.html` | Cookie-based auth, single code input, remove register |
| Modify | `README.md` | Update auth flow description |
| Modify | `CLAUDE.md` | Update arch overview, env vars, test patterns |

---

## Task 1: Database Migration

**Files:**
- Create: `migrations/002_login_codes.sql`

- [ ] **Step 1: Write the migration**

```sql
-- migrations/002_login_codes.sql

CREATE TABLE login_codes (
    id          SERIAL PRIMARY KEY,
    code        VARCHAR(8)   UNIQUE NOT NULL,
    tg_id       BIGINT       NOT NULL REFERENCES users(tg_id) ON DELETE CASCADE,
    expires_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW() + INTERVAL '24 hours',
    used        BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_login_codes_tg_id   ON login_codes(tg_id);
CREATE INDEX idx_login_codes_expires ON login_codes(expires_at);

DROP TABLE IF EXISTS magic_tokens;
```

- [ ] **Step 2: Commit**

```bash
git add migrations/002_login_codes.sql
git commit -m "feat: add login_codes migration, drop magic_tokens"
```

---

## Task 2: Config Updates

**Files:**
- Modify: `app/core/config.py`

- [ ] **Step 1: Add four new fields to Settings**

Replace the contents of `app/core/config.py` with:

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30
    telegram_bot_token: str
    telegram_bot_username: str = ""
    yookassa_shop_id: str
    yookassa_secret_key: str
    xui_api_url: str
    xui_subscription_url: str = ""
    xui_login: str
    xui_password: str
    xui_inbound_id: int = 1
    admin_tg_ids: list[int] = []
    login_code_ttl_hours: int = 24
    bot_secret_key: str = ""
    webhook_base_url: str
    disable_webhook_ip_check: bool = False
    csrf_enabled: bool = True

    log_level: str = "INFO"
    log_file: str = ""
    log_format: str = "detailed"


settings = Settings()
```

- [ ] **Step 2: Add new vars to `.env.example`**

Append to `.env.example`:
```
TELEGRAM_BOT_USERNAME=MyVpnBot
BOT_SECRET_KEY=change-me-strong-random-secret
LOGIN_CODE_TTL_HOURS=24
CSRF_ENABLED=true
```

- [ ] **Step 3: Commit**

```bash
git add app/core/config.py .env.example
git commit -m "feat: add bot_secret_key, login_code_ttl_hours, telegram_bot_username, csrf_enabled to config"
```

---

## Task 3: Test Infrastructure — Disable CSRF in Tests

**Files:**
- Modify: `tests/conftest.py`

- [ ] **Step 1: Add autouse fixture to patch csrf_enabled**

Append to `tests/conftest.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_conn():
    """Создаёт mock-соединение asyncpg с методами, работающими как async."""
    mock_conn = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=[])
    mock_conn.fetchrow = AsyncMock(return_value=None)
    mock_conn.fetchval = AsyncMock(return_value=None)
    mock_conn.execute = AsyncMock(return_value="")

    mock_pool = MagicMock()
    mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

    return mock_conn, mock_pool


@pytest.fixture(autouse=True)
def disable_csrf(monkeypatch):
    """Отключает CSRF middleware в тестах."""
    from app.core import config
    monkeypatch.setattr(config.settings, "csrf_enabled", False)
```

- [ ] **Step 2: Commit**

```bash
git add tests/conftest.py
git commit -m "test: disable CSRF middleware in all tests via autouse fixture"
```

---

## Task 4: Security Utilities

**Files:**
- Modify: `app/core/security.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_security_utils.py`:

```python
import pytest
from app.core.security import generate_login_code


def test_generate_login_code_length():
    code = generate_login_code()
    assert len(code) == 8


def test_generate_login_code_charset():
    code = generate_login_code()
    assert code.isalnum()
    assert code == code.upper()


def test_generate_login_code_unique():
    codes = {generate_login_code() for _ in range(100)}
    assert len(codes) == 100
```

- [ ] **Step 2: Run to verify failures**

```bash
pytest tests/test_security_utils.py -v
```

Expected: `ImportError` or `AttributeError` — `generate_login_code` doesn't exist yet.

- [ ] **Step 3: Add new functions to `app/core/security.py`**

Replace the full contents of `app/core/security.py`:

```python
import secrets
import string
from datetime import datetime, timedelta, timezone
from fastapi import Response
from passlib.context import CryptContext
from jose import JWTError, jwt
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

_CODE_CHARSET = string.ascii_uppercase + string.digits


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_token(data: dict, expires_delta: timedelta) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + expires_delta
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_access_token(data: dict) -> str:
    return create_token(data, timedelta(minutes=settings.access_token_expire_minutes))


def create_refresh_token(data: dict) -> str:
    return create_token(data, timedelta(days=settings.refresh_token_expire_days))


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError as e:
        raise ValueError(f"Invalid token: {e}")


def generate_login_code() -> str:
    return "".join(secrets.choice(_CODE_CHARSET) for _ in range(8))


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    csrf_token = secrets.token_hex(32)
    response.set_cookie(
        "access_token", access_token,
        httponly=True, samesite="strict",
        max_age=settings.access_token_expire_minutes * 60,
    )
    response.set_cookie(
        "refresh_token", refresh_token,
        httponly=True, samesite="strict",
        max_age=settings.refresh_token_expire_days * 24 * 3600,
    )
    response.set_cookie(
        "csrf_token", csrf_token,
        httponly=False, samesite="strict",
        max_age=settings.refresh_token_expire_days * 24 * 3600,
    )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie("access_token", samesite="strict")
    response.delete_cookie("refresh_token", samesite="strict")
    response.delete_cookie("csrf_token", samesite="strict")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_security_utils.py -v
```

Expected: all 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add app/core/security.py tests/test_security_utils.py
git commit -m "feat: add generate_login_code, set_auth_cookies, clear_auth_cookies"
```

---

## Task 5: LoginCodes Repository

**Files:**
- Create: `app/repositories/login_codes.py`
- Test: `tests/test_login_codes_repo.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_login_codes_repo.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone
from app.repositories.login_codes import LoginCodesRepo


@pytest.mark.asyncio
async def test_create_returns_code_and_expires_at():
    repo = LoginCodesRepo()
    conn = AsyncMock()
    fake_expires = datetime(2026, 4, 20, 10, 0, 0, tzinfo=timezone.utc)
    conn.fetchrow = AsyncMock(return_value={"code": "ABCD1234", "expires_at": fake_expires})

    with patch("app.repositories.login_codes.generate_login_code", return_value="ABCD1234"):
        code, expires_at = await repo.create(conn, tg_id=123, ttl_hours=24)

    assert code == "ABCD1234"
    assert expires_at == fake_expires
    conn.fetchrow.assert_called_once()
    args = conn.fetchrow.call_args[0]
    assert "INSERT INTO login_codes" in args[0]
    assert args[1] == "ABCD1234"
    assert args[2] == 123


@pytest.mark.asyncio
async def test_consume_valid_code():
    repo = LoginCodesRepo()
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value={"id": 1, "code": "ABCD1234", "tg_id": 123, "used": True})

    result = await repo.consume(conn, "abcd1234")  # lowercase — should be uppercased

    assert result is not None
    assert result["tg_id"] == 123
    args = conn.fetchrow.call_args[0]
    assert "ABCD1234" in args  # uppercased


@pytest.mark.asyncio
async def test_consume_invalid_code_returns_none():
    repo = LoginCodesRepo()
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=None)

    result = await repo.consume(conn, "BADCODE1")

    assert result is None
```

- [ ] **Step 2: Run to verify failures**

```bash
pytest tests/test_login_codes_repo.py -v
```

Expected: `ModuleNotFoundError` — `login_codes.py` doesn't exist yet.

- [ ] **Step 3: Create `app/repositories/login_codes.py`**

```python
import asyncpg
from datetime import datetime, timedelta, timezone
from typing import Optional
from app.core.security import generate_login_code


class LoginCodesRepo:
    async def create(
        self, conn: asyncpg.Connection, tg_id: int, ttl_hours: int
    ) -> tuple[str, datetime]:
        code = generate_login_code()
        expires_at = datetime.now(timezone.utc) + timedelta(hours=ttl_hours)
        row = await conn.fetchrow(
            "INSERT INTO login_codes (code, tg_id, expires_at) VALUES ($1, $2, $3) RETURNING code, expires_at",
            code, tg_id, expires_at,
        )
        return row["code"], row["expires_at"]

    async def consume(self, conn: asyncpg.Connection, code: str) -> Optional[asyncpg.Record]:
        """Атомарно отмечает код использованным. Защита от TOCTOU."""
        return await conn.fetchrow(
            """
            UPDATE login_codes
            SET used = TRUE
            WHERE code = $1
              AND used = FALSE
              AND expires_at > NOW()
            RETURNING *
            """,
            code.upper(),
        )
```

- [ ] **Step 4: Run tests to verify pass**

```bash
pytest tests/test_login_codes_repo.py -v
```

Expected: all 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add app/repositories/login_codes.py tests/test_login_codes_repo.py
git commit -m "feat: add LoginCodesRepo with create and consume methods"
```

---

## Task 6: Update get_current_user to Read from Cookie

**Files:**
- Modify: `app/core/dependencies.py`

- [ ] **Step 1: Replace Bearer auth with cookie auth**

Replace the full contents of `app/core/dependencies.py`:

```python
from typing import AsyncGenerator
from fastapi import Depends, HTTPException, Request, status
import asyncpg
from app.core.database import get_pool
from app.core.security import decode_token


async def get_conn() -> AsyncGenerator[asyncpg.Connection, None]:
    try:
        pool = get_pool()
    except RuntimeError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        )
    async with pool.acquire() as conn:
        yield conn


async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = decode_token(token)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    if not payload.get("sub"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    return payload


async def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user
```

- [ ] **Step 2: Run existing tests to ensure nothing is broken**

```bash
pytest tests/ -v --ignore=tests_e2e
```

Expected: all tests that were passing before still pass. Any that used `Authorization: Bearer` headers will now need to use the cookie approach — but since those tests mock `get_current_user` via `app.dependency_overrides`, they should be unaffected.

- [ ] **Step 3: Commit**

```bash
git add app/core/dependencies.py
git commit -m "feat: get_current_user reads from access_token cookie instead of Bearer header"
```

---

## Task 7: CSRF Middleware

**Files:**
- Create: `app/core/csrf.py`
- Modify: `app/main.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_csrf.py`:

```python
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture(autouse=True)
def enable_csrf_for_this_module(monkeypatch):
    """Re-enable CSRF for these specific tests."""
    from app.core import config
    monkeypatch.setattr(config.settings, "csrf_enabled", True)


@pytest.mark.asyncio
async def test_csrf_blocks_post_without_token():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.post("/api/v1/keys/", json={})
    assert resp.status_code == 403
    assert "CSRF" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_csrf_allows_post_with_matching_token():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        c.cookies.set("csrf_token", "test-csrf-value")
        resp = await c.post(
            "/api/v1/keys/",
            json={},
            headers={"X-CSRF-Token": "test-csrf-value"},
        )
    # Not 403 (may be 401/422 from missing auth/body — that's fine)
    assert resp.status_code != 403


@pytest.mark.asyncio
async def test_csrf_allows_auth_endpoints_without_token():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.post("/api/v1/auth/login", json={"code": "TESTCODE1"})
    # Not 403 (may be 400/422 from bad code — that's fine)
    assert resp.status_code != 403


@pytest.mark.asyncio
async def test_csrf_allows_bot_endpoint_without_token():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.post(
            "/api/v1/bot/auth/generate-code",
            json={"tg_id": 123},
            headers={"X-Bot-Secret": "test"},
        )
    assert resp.status_code != 403


@pytest.mark.asyncio
async def test_csrf_allows_get_requests():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get("/api/v1/auth/me")
    assert resp.status_code != 403
```

- [ ] **Step 2: Run to verify failures**

```bash
pytest tests/test_csrf.py -v
```

Expected: `ImportError` from `app/core/csrf.py` not existing yet.

- [ ] **Step 3: Create `app/core/csrf.py`**

```python
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from app.core.config import settings

_EXEMPT_PREFIXES = (
    "/api/v1/auth/",
    "/api/v1/bot/",
)
_EXEMPT_EXACT = {"/api/v1/payments/webhook"}
_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not settings.csrf_enabled:
            return await call_next(request)
        if request.method in _SAFE_METHODS:
            return await call_next(request)
        path = request.url.path
        if path in _EXEMPT_EXACT:
            return await call_next(request)
        for prefix in _EXEMPT_PREFIXES:
            if path.startswith(prefix):
                return await call_next(request)
        csrf_cookie = request.cookies.get("csrf_token")
        csrf_header = request.headers.get("X-CSRF-Token")
        if not csrf_cookie or csrf_cookie != csrf_header:
            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF validation failed"},
            )
        return await call_next(request)
```

- [ ] **Step 4: Register middleware + bot router in `app/main.py`**

Replace the full contents of `app/main.py`:

```python
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.core.database import create_pool, close_pool
from app.core.logging import setup_logging, get_logger
from app.core.csrf import CSRFMiddleware
from app.api import auth, keys, tariffs, payments, admin, bot
from app.core.config import settings

setup_logging(
    log_level=settings.log_level,
    log_file=settings.log_file or None,
    log_format=settings.log_format,
)

logger = get_logger(__name__)

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Запуск приложения VPN Web Backend")
    await create_pool()
    logger.info("Подключение к базе данных установлено")
    yield
    await close_pool()
    logger.info("Приложение завершает работу")


app = FastAPI(title="VPN Web Backend", version="1.0.0", lifespan=lifespan)

app.add_middleware(CSRFMiddleware)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(bot.router, prefix="/api/v1/bot", tags=["bot"])
app.include_router(keys.router, prefix="/api/v1/keys", tags=["keys"])
app.include_router(tariffs.router, prefix="/api/v1/tariffs", tags=["tariffs"])
app.include_router(payments.router, prefix="/api/v1/payments", tags=["payments"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/")
async def serve_frontend():
    return FileResponse(FRONTEND_DIR / "index.html")


app.mount("/", StaticFiles(directory=str(FRONTEND_DIR)), name="frontend")
```

- [ ] **Step 5: Run tests to verify pass**

```bash
pytest tests/test_csrf.py -v
```

Expected: all 5 tests PASS (some may get 401/422/400 — important thing is none get 403 where they shouldn't).

- [ ] **Step 6: Commit**

```bash
git add app/core/csrf.py app/main.py
git commit -m "feat: add CSRFMiddleware with double-submit cookie pattern"
```

---

## Task 8: Update Schemas

**Files:**
- Modify: `app/schemas/auth.py`

- [ ] **Step 1: Replace schema file**

Replace the full contents of `app/schemas/auth.py`:

```python
from pydantic import BaseModel
from typing import Optional


class LoginCodeRequest(BaseModel):
    code: str


class UserInfoResponse(BaseModel):
    id: int
    tg_id: Optional[int] = None
    is_admin: bool


class GenerateCodeRequest(BaseModel):
    tg_id: int


class GenerateCodeResponse(BaseModel):
    code: str
    expires_at: str
```

- [ ] **Step 2: Commit**

```bash
git add app/schemas/auth.py
git commit -m "feat: replace auth schemas — remove email/password, add code login and bot schemas"
```

---

## Task 9: Auth Service Refactor

**Files:**
- Modify: `app/services/auth.py`
- Test: `tests/test_auth_service.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_auth_service.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException
from app.services.auth import login_with_code, refresh_tokens_from_cookie
from app.core.security import create_refresh_token


@pytest.mark.asyncio
async def test_login_with_valid_code_existing_user():
    conn = AsyncMock()
    fake_record = {"id": 1, "code": "ABCD1234", "tg_id": 123, "used": True}
    fake_user = {"id": 42, "tg_id": 123, "email": "tg_123@bot.local"}

    with (
        patch("app.services.auth.login_codes_repo.consume", return_value=fake_record),
        patch("app.services.auth.web_users_repo.get_by_tg_id", return_value=fake_user),
    ):
        access_token, refresh_token = await login_with_code(conn, "ABCD1234")

    assert access_token
    assert refresh_token


@pytest.mark.asyncio
async def test_login_with_valid_code_new_user_creates_web_user():
    conn = AsyncMock()
    fake_record = {"id": 1, "code": "ABCD1234", "tg_id": 456, "used": True}
    new_user = {"id": 99, "tg_id": 456, "email": "tg_456@bot.local"}

    with (
        patch("app.services.auth.login_codes_repo.consume", return_value=fake_record),
        patch("app.services.auth.web_users_repo.get_by_tg_id", return_value=None),
        patch("app.services.auth.web_users_repo.create", return_value=new_user) as mock_create,
    ):
        access_token, refresh_token = await login_with_code(conn, "ABCD1234")

    mock_create.assert_called_once()
    call_kwargs = mock_create.call_args[1]
    assert call_kwargs["email"] == "tg_456@bot.local"
    assert access_token


@pytest.mark.asyncio
async def test_login_with_invalid_code_raises_400():
    conn = AsyncMock()

    with patch("app.services.auth.login_codes_repo.consume", return_value=None):
        with pytest.raises(HTTPException) as exc_info:
            await login_with_code(conn, "BADCODE1")

    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_refresh_tokens_from_cookie_valid():
    payload = {"sub": "42", "tg_id": 123, "is_admin": False}
    refresh_token = create_refresh_token(payload)

    access_token, new_refresh = await refresh_tokens_from_cookie(refresh_token)

    assert access_token
    assert new_refresh


@pytest.mark.asyncio
async def test_refresh_tokens_from_cookie_invalid_raises_401():
    with pytest.raises(HTTPException) as exc_info:
        await refresh_tokens_from_cookie("invalid.token.here")

    assert exc_info.value.status_code == 401
```

- [ ] **Step 2: Run to verify failures**

```bash
pytest tests/test_auth_service.py -v
```

Expected: `ImportError` — service functions don't exist yet.

- [ ] **Step 3: Replace `app/services/auth.py`**

```python
import secrets
import asyncpg
from fastapi import HTTPException, status
from app.repositories.web_users import WebUsersRepo
from app.repositories.login_codes import LoginCodesRepo
from app.repositories.users import UsersRepo
from app.core.security import hash_password, create_access_token, create_refresh_token, decode_token
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

web_users_repo = WebUsersRepo()
login_codes_repo = LoginCodesRepo()
users_repo = UsersRepo()


def _is_admin(tg_id: int | None) -> bool:
    return tg_id in settings.admin_tg_ids if tg_id else False


def _build_tokens(user_id: int, tg_id: int | None) -> dict:
    payload = {"sub": str(user_id), "tg_id": tg_id, "is_admin": _is_admin(tg_id)}
    return {
        "access_token": create_access_token(payload),
        "refresh_token": create_refresh_token(payload),
    }


async def login_with_code(conn: asyncpg.Connection, code: str) -> tuple[str, str]:
    record = await login_codes_repo.consume(conn, code)
    if not record:
        logger.warning("Недействительный или просроченный код входа")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Code invalid or expired")
    tg_id = record["tg_id"]
    user = await web_users_repo.get_by_tg_id(conn, tg_id)
    if not user:
        user = await web_users_repo.create(
            conn,
            email=f"tg_{tg_id}@bot.local",
            password_hash=hash_password(secrets.token_hex(32)),
            tg_id=tg_id,
        )
        logger.info("Создан новый web_users для tg_id=%d", tg_id)
    tokens = _build_tokens(user["id"], tg_id)
    return tokens["access_token"], tokens["refresh_token"]


async def refresh_tokens_from_cookie(refresh_token: str) -> tuple[str, str]:
    try:
        payload = decode_token(refresh_token)
    except ValueError:
        logger.warning("Недействительный refresh token")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    tg_id = payload.get("tg_id")
    new_payload = {"sub": payload["sub"], "tg_id": tg_id, "is_admin": _is_admin(tg_id)}
    return create_access_token(new_payload), create_refresh_token(new_payload)
```

- [ ] **Step 4: Run tests to verify pass**

```bash
pytest tests/test_auth_service.py -v
```

Expected: all 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add app/services/auth.py tests/test_auth_service.py
git commit -m "feat: replace auth service with login_with_code and refresh_tokens_from_cookie"
```

---

## Task 10: Auth API Endpoints

**Files:**
- Modify: `app/api/auth.py`
- Test: `tests/test_auth.py`

- [ ] **Step 1: Write failing tests**

Replace the full contents of `tests/test_auth.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.dependencies import get_conn
from app.core.security import create_access_token, create_refresh_token


@pytest.fixture
async def client(mock_conn):
    mock_conn_obj, mock_pool = mock_conn

    async def override_get_conn():
        yield mock_conn_obj

    app.dependency_overrides[get_conn] = override_get_conn
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_login_with_valid_code_sets_cookies(client):
    fake_record = {"id": 1, "code": "ABCD1234", "tg_id": 123, "used": True}
    fake_user = {"id": 42, "tg_id": 123, "email": "tg_123@bot.local"}

    with (
        patch("app.services.auth.login_codes_repo.consume", return_value=fake_record),
        patch("app.services.auth.web_users_repo.get_by_tg_id", return_value=fake_user),
    ):
        resp = await client.post("/api/v1/auth/login", json={"code": "ABCD1234"})

    assert resp.status_code == 200
    assert "access_token" in resp.cookies
    assert "refresh_token" in resp.cookies
    assert "csrf_token" in resp.cookies


@pytest.mark.asyncio
async def test_login_with_invalid_code_returns_400(client):
    with patch("app.services.auth.login_codes_repo.consume", return_value=None):
        resp = await client.post("/api/v1/auth/login", json={"code": "BADCODE1"})

    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_me_returns_user_info(client):
    payload = {"sub": "42", "tg_id": 123, "is_admin": False}
    token = create_access_token(payload)
    client.cookies.set("access_token", token)

    resp = await client.get("/api/v1/auth/me")

    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == 42
    assert data["tg_id"] == 123
    assert data["is_admin"] is False


@pytest.mark.asyncio
async def test_me_without_cookie_returns_401(client):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_logout_clears_cookies(client):
    resp = await client.post("/api/v1/auth/logout")
    assert resp.status_code == 200
    # Cookies should be deleted (max-age=0 or expires in past)
    assert "access_token" in resp.headers.get("set-cookie", "")


@pytest.mark.asyncio
async def test_refresh_with_valid_cookie(client):
    payload = {"sub": "42", "tg_id": 123, "is_admin": False}
    refresh_token = create_refresh_token(payload)
    client.cookies.set("refresh_token", refresh_token)

    resp = await client.post("/api/v1/auth/refresh")

    assert resp.status_code == 200
    assert "access_token" in resp.cookies


@pytest.mark.asyncio
async def test_refresh_without_cookie_returns_401(client):
    resp = await client.post("/api/v1/auth/refresh")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_config_returns_bot_username(client):
    with patch("app.api.auth.settings") as mock_settings:
        mock_settings.telegram_bot_username = "TestVpnBot"
        resp = await client.get("/api/v1/auth/config")

    assert resp.status_code == 200
    assert resp.json()["telegram_bot_username"] == "TestVpnBot"
```

- [ ] **Step 2: Run to verify failures**

```bash
pytest tests/test_auth.py -v
```

Expected: failures — endpoints don't match yet.

- [ ] **Step 3: Replace `app/api/auth.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
import asyncpg
from app.core.dependencies import get_conn, get_current_user
from app.core.security import set_auth_cookies, clear_auth_cookies
from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.auth import LoginCodeRequest, UserInfoResponse
from app.services import auth as auth_service

router = APIRouter()
logger = get_logger(__name__)


@router.post("/login")
async def login(
    body: LoginCodeRequest,
    response: Response,
    conn: asyncpg.Connection = Depends(get_conn),
):
    logger.info("Попытка входа по коду")
    access_token, refresh_token = await auth_service.login_with_code(conn, body.code)
    set_auth_cookies(response, access_token, refresh_token)
    logger.info("Успешный вход по коду")
    return {"message": "ok"}


@router.get("/me", response_model=UserInfoResponse)
async def me(current_user: dict = Depends(get_current_user)):
    return {
        "id": int(current_user["sub"]),
        "tg_id": current_user.get("tg_id"),
        "is_admin": current_user.get("is_admin", False),
    }


@router.post("/logout")
async def logout(response: Response):
    clear_auth_cookies(response)
    return {"message": "ok"}


@router.post("/refresh")
async def refresh(request: Request, response: Response):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh token")
    access_token, new_refresh_token = await auth_service.refresh_tokens_from_cookie(refresh_token)
    set_auth_cookies(response, access_token, new_refresh_token)
    return {"message": "ok"}


@router.get("/config")
async def config():
    return {"telegram_bot_username": settings.telegram_bot_username}
```

- [ ] **Step 4: Run tests to verify pass**

```bash
pytest tests/test_auth.py -v
```

Expected: all 8 tests PASS.

- [ ] **Step 5: Run full suite to check no regressions**

```bash
pytest tests/ -v --ignore=tests_e2e
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add app/api/auth.py tests/test_auth.py
git commit -m "feat: replace auth endpoints — code login, cookie sessions, /me, /logout, /config"
```

---

## Task 11: Bot API Endpoint

**Files:**
- Create: `app/api/bot.py`
- Test: `tests/test_bot_auth.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_bot_auth.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.dependencies import get_conn
from app.core.config import settings


@pytest.fixture
async def client(mock_conn, monkeypatch):
    mock_conn_obj, _ = mock_conn
    monkeypatch.setattr(settings, "bot_secret_key", "test-secret")

    async def override_get_conn():
        yield mock_conn_obj

    app.dependency_overrides[get_conn] = override_get_conn
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_generate_code_valid(client):
    fake_user = {"tg_id": 123, "username": "alice"}
    fake_expires = datetime(2026, 4, 20, 10, 0, 0, tzinfo=timezone.utc)

    with (
        patch("app.api.bot.users_repo.get_by_tg_id", return_value=fake_user),
        patch("app.api.bot.login_codes_repo.create", return_value=("ABCD1234", fake_expires)),
    ):
        resp = await client.post(
            "/api/v1/bot/auth/generate-code",
            json={"tg_id": 123},
            headers={"X-Bot-Secret": "test-secret"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == "ABCD1234"
    assert "expires_at" in data


@pytest.mark.asyncio
async def test_generate_code_wrong_secret(client):
    resp = await client.post(
        "/api/v1/bot/auth/generate-code",
        json={"tg_id": 123},
        headers={"X-Bot-Secret": "wrong-secret"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_generate_code_missing_secret(client):
    resp = await client.post(
        "/api/v1/bot/auth/generate-code",
        json={"tg_id": 123},
    )
    assert resp.status_code == 422  # missing required header


@pytest.mark.asyncio
async def test_generate_code_unknown_tg_id(client):
    with patch("app.api.bot.users_repo.get_by_tg_id", return_value=None):
        resp = await client.post(
            "/api/v1/bot/auth/generate-code",
            json={"tg_id": 999},
            headers={"X-Bot-Secret": "test-secret"},
        )
    assert resp.status_code == 404
```

- [ ] **Step 2: Run to verify failures**

```bash
pytest tests/test_bot_auth.py -v
```

Expected: `ModuleNotFoundError` — `app/api/bot.py` doesn't exist yet.

- [ ] **Step 3: Create `app/api/bot.py`**

```python
from fastapi import APIRouter, Depends, Header, HTTPException, status
import asyncpg
from app.core.dependencies import get_conn
from app.core.config import settings
from app.core.logging import get_logger
from app.repositories.login_codes import LoginCodesRepo
from app.repositories.users import UsersRepo
from app.schemas.auth import GenerateCodeRequest, GenerateCodeResponse

router = APIRouter()
logger = get_logger(__name__)

login_codes_repo = LoginCodesRepo()
users_repo = UsersRepo()


def _verify_bot_secret(x_bot_secret: str = Header(...)) -> None:
    if x_bot_secret != settings.bot_secret_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid bot secret")


@router.post("/auth/generate-code", response_model=GenerateCodeResponse)
async def generate_code(
    body: GenerateCodeRequest,
    conn: asyncpg.Connection = Depends(get_conn),
    _: None = Depends(_verify_bot_secret),
):
    user = await users_repo.get_by_tg_id(conn, body.tg_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    code, expires_at = await login_codes_repo.create(conn, body.tg_id, settings.login_code_ttl_hours)
    logger.info("Код входа создан для tg_id=%d", body.tg_id)
    return {"code": code, "expires_at": expires_at.isoformat()}
```

- [ ] **Step 4: Run tests to verify pass**

```bash
pytest tests/test_bot_auth.py -v
```

Expected: all 4 tests PASS.

- [ ] **Step 5: Run full suite**

```bash
pytest tests/ -v --ignore=tests_e2e
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add app/api/bot.py tests/test_bot_auth.py
git commit -m "feat: add bot API endpoint POST /bot/auth/generate-code"
```

---

## Task 12: Frontend — Cookie Auth + Code Login Form

**Files:**
- Modify: `frontend/index.html`

This task modifies several distinct sections of the 1878-line single-file SPA. Make each change independently.

### 12a: Update API Client (lines 705–790)

- [ ] **Step 1: Replace API.request to send CSRF header and remove Bearer token logic**

Find the `API.request` function (starting at line 705) and replace the entire `API = { ... }` block (lines 705–790) with:

```javascript
const API = {
    getCsrfToken() {
        const match = document.cookie.match(/(?:^|;)\s*csrf_token=([^;]+)/);
        return match ? decodeURIComponent(match[1]) : '';
    },

    async request(method, path, body = null) {
        const opts = {
            method,
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin',
        };
        if (method !== 'GET' && method !== 'HEAD') {
            const csrf = this.getCsrfToken();
            if (csrf) opts.headers['X-CSRF-Token'] = csrf;
        }
        if (body !== null) {
            opts.body = JSON.stringify(body);
            Logger.log('API', '  Тело:', JSON.stringify(body));
        }

        const url = `/api/v1${path}`;
        Logger.log('API', `→ ${method} ${url}`);

        let resp;
        try {
            resp = await fetch(url, opts);
            Logger.log('API', '  ← Статус:', resp.status, resp.statusText);
        } catch (err) {
            Logger.error('API', '  ✗ Сетевая ошибка:', err.message);
            throw new Error(`Сетевая ошибка: ${err.message}`);
        }

        if (resp.status === 401) {
            Logger.warn('API', '  ⚠ 401 — попытка обновления токена');
            if (path === '/auth/refresh') {
                Logger.error('API', '  ✗ Refresh тоже истёк — logout');
                await Auth.logout();
                throw new Error('Необходима авторизация');
            }
            const refreshed = await Auth.refresh();
            if (refreshed) {
                Logger.log('API', '  ✓ Токен обновлён — повторный запрос');
                const resp2 = await fetch(url, opts);
                Logger.log('API', '  ← Повторный статус:', resp2.status);
                return await this._handleResp(resp2);
            }
            await Auth.logout();
            throw new Error('Необходима авторизация');
        }

        if (resp.status === 204) return null;
        return await this._handleResp(resp);
    },

    async _handleResp(resp) {
        if (!resp.ok) {
            let msg = `Ошибка ${resp.status}`;
            try {
                const data = await resp.json();
                Logger.warn('API', '  ✗ Ответ ошибки:', JSON.stringify(data));
                if (data.detail) {
                    msg = Array.isArray(data.detail)
                        ? data.detail.map(d => d.msg).join(', ')
                        : data.detail;
                }
            } catch (_) {}
            throw new Error(msg);
        }
        const data = await resp.json();
        if (Array.isArray(data)) {
            Logger.log('API', `  ← Массив: ${data.length} элементов`);
        } else {
            Logger.log('API', '  ← Данные:', Object.keys(data).join(', '));
        }
        return data;
    },

    get(path) { return this.request('GET', path); },
    post(path, body) { return this.request('POST', path, body); },
    patch(path, body) { return this.request('PATCH', path, body); },
    delete(path) { return this.request('DELETE', path); },
};
```

### 12b: Replace Auth Class (lines 795–936)

- [ ] **Step 2: Replace the entire `Auth = { ... }` block (lines 795–936) with:**

```javascript
const Auth = {
    _userInfo: null,

    async isLoggedIn() {
        if (this._userInfo) return true;
        try {
            this._userInfo = await API.get('/auth/me');
            Logger.log('Auth', '  isLoggedIn → true, id=', this._userInfo.id);
            return true;
        } catch (_) {
            Logger.log('Auth', '  isLoggedIn → false');
            return false;
        }
    },

    async isAdmin() {
        if (!this._userInfo) await this.isLoggedIn();
        const result = this._userInfo ? (this._userInfo.is_admin === true) : false;
        Logger.log('Auth', '  isAdmin →', result);
        return result;
    },

    async login(code) {
        Logger.group('Auth', 'login по коду');
        try {
            await API.post('/auth/login', { code });
            this._userInfo = null; // reset cache — will be fetched on next isLoggedIn()
            Logger.log('Auth', '  ✓ Вход успешен');
        } catch (err) {
            Logger.error('Auth', '  ✗ Ошибка входа:', err.message);
            throw err;
        } finally {
            Logger.groupEnd();
        }
    },

    async refresh() {
        Logger.log('Auth', '  refresh: попытка обновления');
        try {
            await API.post('/auth/refresh');
            this._userInfo = null;
            Logger.log('Auth', '  ✓ Токен обновлён');
            return true;
        } catch (err) {
            Logger.error('Auth', '  ✗ Ошибка обновления токена:', err.message);
            return false;
        }
    },

    async logout() {
        Logger.group('Auth', 'logout');
        try {
            await API.post('/auth/logout');
        } catch (_) {}
        this._userInfo = null;
        Logger.log('Auth', '  Редирект на #/login');
        Logger.groupEnd();
        Router.navigate('#/login');
    },
};
```

### 12c: Update Router (lines 976–985)

- [ ] **Step 3: Remove `#/register` route**

Find the `routes:` object (line 978) and replace:

```javascript
    routes: {
        '#/login': { page: 'login', auth: false },
        '#/register': { page: 'register', auth: false },
        '#/dashboard': { page: 'dashboard', auth: true },
        '#/tariffs': { page: 'tariffs', auth: false },
        '#/payments': { page: 'payments', auth: true },
        '#/admin': { page: 'admin', auth: true, admin: true },
    },
```

with:

```javascript
    routes: {
        '#/login': { page: 'login', auth: false },
        '#/dashboard': { page: 'dashboard', auth: true },
        '#/tariffs': { page: 'tariffs', auth: false },
        '#/payments': { page: 'payments', auth: true },
        '#/admin': { page: 'admin', auth: true, admin: true },
    },
```

### 12d: Update Router.handle to use async Auth.isLoggedIn

- [ ] **Step 4: Update route guard in `Router.handle` (around line 1020)**

Find:

```javascript
        if (route.auth && !Auth.isLoggedIn()) {
```

Replace with:

```javascript
        if (route.auth && !(await Auth.isLoggedIn())) {
```

Find:

```javascript
        if (route.admin && !Auth.isAdmin()) {
```

Replace with:

```javascript
        if (route.admin && !(await Auth.isAdmin())) {
```

Also make `handle()` async — find:

```javascript
    handle() {
```

Replace with:

```javascript
    async handle() {
```

### 12e: Update Router.renderers — remove register

- [ ] **Step 5: Remove `register: Pages.register` from renderers**

Find in `Router.render`:

```javascript
        const renderers = {
            login: Pages.login,
            register: Pages.register,
```

Replace with:

```javascript
        const renderers = {
            login: Pages.login,
```

### 12f: Replace Login Page (lines 1130–1237)

- [ ] **Step 6: Replace the `login(container)` method body**

Find the entire `login(container) { ... }` block (lines 1130–1237) and replace it with:

```javascript
    async login(container) {
        // Fetch bot username for the help link
        let botUsername = '';
        try {
            const cfg = await API.get('/auth/config');
            botUsername = cfg.telegram_bot_username || '';
        } catch (_) {}

        const botLink = botUsername
            ? `<a href="https://t.me/${botUsername}" target="_blank" rel="noopener">@${botUsername}</a>`
            : 'нашего Telegram-бота';

        container.innerHTML = `
        <div class="auth-container">
            <div class="auth-card">
                <h1>Вход</h1>
                <p class="subtitle">Получите код в ${botLink} и введите его ниже</p>
                <form id="loginForm">
                    <div class="form-group">
                        <label for="loginCode">Код от бота</label>
                        <input type="text" id="loginCode" class="form-input"
                               placeholder="ABCD1234" required autocomplete="off"
                               maxlength="8" style="text-transform:uppercase;letter-spacing:0.15em">
                    </div>
                    <button type="submit" class="btn btn-primary" id="loginBtn">Войти</button>
                </form>
            </div>
        </div>`;

        document.getElementById('loginForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = document.getElementById('loginBtn');
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner"></span>';
            Logger.group('Pages', 'loginForm: submit');
            try {
                const code = document.getElementById('loginCode').value.trim().toUpperCase();
                Logger.log('Pages', '  code:', code);
                await Auth.login(code);
                Toast.success('Вы успешно вошли!');
                Logger.log('Pages', '  Редирект на #/dashboard');
                Router.navigate('#/dashboard');
            } catch (err) {
                Logger.error('Pages', '  ✗ Ошибка входа:', err.message);
                Toast.error(err.message);
            } finally {
                btn.disabled = false;
                btn.textContent = 'Войти';
                Logger.groupEnd();
            }
        });
    },
```

### 12g: Remove Register Page (lines 1239–1291)

- [ ] **Step 7: Delete the entire `register(container)` method**

Find and delete the block from `// ===== REGISTER =====` (line 1239) through the closing `},` of `register(container)` (line 1291, inclusive).

### 12h: Update navigation links that reference `#/register`

- [ ] **Step 8: Search and remove any remaining register links**

```bash
grep -n "register" frontend/index.html
```

Remove any `<a href="#/register">` anchors and any nav items referencing register. Also check `updateNav` in Router — remove the register case if present.

### 12i: Fix initialization block (lines 1855–1874)

The DOMContentLoaded handler at the bottom of the file calls `Auth.isLoggedIn()` synchronously and references `#/register`. Both must be fixed.

- [ ] **Step 9: Replace the initialization block**

Find the block starting with `// Auto-redirect if already logged in` (around line 1856) through `Router.init();` (line 1873) and replace it with:

```javascript
    // Auto-redirect based on auth state
    const hash = window.location.hash || '#/login';
    const isLoggedIn = await Auth.isLoggedIn();
    Logger.log('Init', 'isLoggedIn:', isLoggedIn);

    if (isLoggedIn && hash === '#/login') {
        Logger.log('Init', '  → Авторизован на login — редирект на #/dashboard');
        Router.navigate('#/dashboard');
    } else if (!isLoggedIn && hash !== '#/login' && hash !== '#/tariffs') {
        Logger.log('Init', '  → Не авторизован на защищённой странице — редирект на #/login');
        Router.navigate('#/login');
    } else {
        Logger.log('Init', '  → Маршрут корректен, продолжаем');
    }

    Logger.log('Init', 'Вызов Router.init()');
    Logger.groupEnd();
    await Router.init();
```

Also find the outer DOMContentLoaded wrapper:
```javascript
document.addEventListener('DOMContentLoaded', () => {
```
Replace with:
```javascript
document.addEventListener('DOMContentLoaded', async () => {
```

And make `Router.init()` async — find:
```javascript
    init() {
        Logger.group('Router', 'init');
```
Replace with:
```javascript
    async init() {
        Logger.group('Router', 'init');
```

And in `Router.init`, the hashchange handler should call handle without blocking:
```javascript
        window.addEventListener('hashchange', () => {
            Logger.log('Router', 'hashchange →', window.location.hash || '#/login');
            this.handle().catch(err => Logger.error('Router', 'nav error:', err.message));
        });
```

And the final `this.handle()` call inside `Router.init` should be awaited:
```javascript
        Logger.log('Router', 'Первичная обработка маршрута');
        await this.handle();
```

- [ ] **Step 10: Commit frontend changes**

```bash
git add frontend/index.html
git commit -m "feat: replace frontend auth — single code input, cookie sessions, remove register page"
```

---

## Task 13: Documentation

**Files:**
- Modify: `README.md`
- Modify: `CLAUDE.md`

- [ ] **Step 1: Update `CLAUDE.md` — Auth section**

Find the "**Auth**: JWT-based..." paragraph in `CLAUDE.md`. Replace it with:

```
**Auth**: JWT-based (python-jose). Tokens stored in HttpOnly cookies (`access_token`, `refresh_token`). A JS-readable `csrf_token` cookie is set on login; all state-mutating requests must include it as `X-CSRF-Token` header (CSRF middleware in `app/core/csrf.py`).

One login flow:
- Bot code: Telegram bot calls `POST /api/v1/bot/auth/generate-code` (authenticated with `X-Bot-Secret` header). Backend creates an 8-char alphanumeric code in `login_codes` table (24h TTL). User enters code at website → `POST /api/v1/auth/login` → cookies set.

The `magic_tokens` table has been removed and replaced by `login_codes`.
```

- [ ] **Step 2: Update `CLAUDE.md` — Environment Variables**

In the "Environment Variables" section, replace the Telegram entry and add new vars:

Find:
```
- `TELEGRAM_BOT_TOKEN` — for magic-link sending
```

Replace with:
```
- `TELEGRAM_BOT_TOKEN` — for Telegram bot API calls
- `TELEGRAM_BOT_USERNAME` — bot username shown on login page (e.g. `MyVpnBot`)
- `BOT_SECRET_KEY` — shared secret for `X-Bot-Secret` header on bot API endpoint
- `LOGIN_CODE_TTL_HOURS` — login code validity period (default: 24)
- `CSRF_ENABLED` — set to `false` in tests; default `true`
```

Remove the line about `WEBHOOK_BASE_URL` mentioning magic links (it's now only used for payment redirects).

- [ ] **Step 3: Update `CLAUDE.md` — Test Patterns**

Find the test patterns section. Add a note:

```markdown
For tests of endpoints that use `get_current_user`, the dependency override pattern still works:
```python
app.dependency_overrides[get_current_user] = lambda: {"sub": "1", "tg_id": 123, "is_admin": False}
```

For tests that need cookie-based auth without overriding, set cookies directly:
```python
client.cookies.set("access_token", create_access_token({"sub": "1", "tg_id": 123, "is_admin": False}))
```

CSRF is disabled in all tests via the `disable_csrf` autouse fixture in `conftest.py`.
```

- [ ] **Step 4: Update `README.md` — auth section**

Find the section describing registration/auth flow and replace with:

```markdown
## Authentication Flow

1. User opens the website and sees the login page with a link to the Telegram bot.
2. User opens the bot and receives an 8-character login code.
3. User enters the code on the login page.
4. Backend consumes the code atomically, creates a session (HttpOnly cookies).
5. When the session expires, the user returns to the bot for a new code.

### Bot Integration API

The Telegram bot must call this endpoint to generate codes:

```
POST /api/v1/bot/auth/generate-code
X-Bot-Secret: <BOT_SECRET_KEY>
Content-Type: application/json

{"tg_id": 123456789}
```

Response: `{"code": "X7K2M9PQ", "expires_at": "2026-04-20T10:00:00Z"}`

Returns `404` if `tg_id` is not in the `users` table.
```

- [ ] **Step 5: Commit documentation**

```bash
git add README.md CLAUDE.md
git commit -m "docs: update auth flow description for Telegram-only login"
```

---

## Task 14: Run Full Test Suite and Verify

- [ ] **Step 1: Run all unit tests**

```bash
pytest tests/ -v --ignore=tests_e2e
```

Expected: all tests pass.

- [ ] **Step 2: Apply migration to local dev DB**

```bash
psql "$DATABASE_URL" -f migrations/002_login_codes.sql
```

Expected: no errors.

- [ ] **Step 3: Start the server and verify manually**

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000` — should see single-field login page with bot link.

- [ ] **Step 4: Test bot API endpoint**

```bash
curl -X POST http://localhost:8000/api/v1/bot/auth/generate-code \
  -H "Content-Type: application/json" \
  -H "X-Bot-Secret: $BOT_SECRET_KEY" \
  -d '{"tg_id": YOUR_TG_ID}'
```

Expected: `{"code": "XXXXXXXX", "expires_at": "..."}`.

- [ ] **Step 5: Test login with the generated code**

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"code": "XXXXXXXX"}' \
  -c /tmp/cookies.txt -v
```

Expected: HTTP 200, Set-Cookie headers for `access_token` (HttpOnly), `refresh_token` (HttpOnly), `csrf_token` (not HttpOnly).

- [ ] **Step 6: Test /me with cookies**

```bash
curl http://localhost:8000/api/v1/auth/me \
  -b /tmp/cookies.txt
```

Expected: `{"id": N, "tg_id": YOUR_TG_ID, "is_admin": false}`.

- [ ] **Step 7: Verify DevTools cookies**

Open `http://localhost:8000` in browser, open DevTools → Application → Cookies:
- `access_token`: HttpOnly ✓, SameSite=Strict ✓
- `refresh_token`: HttpOnly ✓, SameSite=Strict ✓
- `csrf_token`: NOT HttpOnly ✓ (JS can read it)

- [ ] **Step 8: Final commit tag**

```bash
git tag v2.0.0-telegram-auth
```
