# Web Backend Implementation Plan (revised for user_system branch)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Создать FastAPI бэкенд для веб-версии VPN сервиса, максимально переиспользуя кодовую базу ветки `user_system`.

**Architecture:** Монолитный FastAPI сервис в отдельном репозитории `vpn-web-backend`. Общая PostgreSQL с ботом. Веб-бэкенд использует `py3xui.AsyncApi` напрямую для 3x-UI операций, `DashboardMetricsService` из `services/analytics/` для статистики, тонкие asyncpg-репозитории для `web_users`/`magic_tokens`.

**Tech Stack:** FastAPI, asyncpg, Pydantic v2, python-jose, passlib[bcrypt], py3xui, yookassa, pytest, Docker

**Источник кода бота:** `/home/claude/Bot_3xui_vpn` (ветка `user_system`)

---

## Ключевые находки из кодовой базы user_system

| Что | Где в боте | Как используется в веб |
|-----|-----------|----------------------|
| `DashboardMetricsService` | `services/analytics/dashboard_metrics.py` | Переиспользуется напрямую для `/admin/stats` |
| `py3xui.AsyncApi` | `client.py` (зависимость) | Используем напрямую без `XUISession` (тот тащит весь DI) |
| `models.User`, `models.Key`, `models.Tariff`, `models.PaymentModel` | `models/` | Переиспользуются как domain objects |
| Схема БД | `assets/schema.sql` | Таблица — `tariff` (не `tariffs`), `payments` имеет `number_of_months`, `discount_percent` |
| `payment_type` формат | `services/core/payment/processor.py` | `"operation|data"` — используем `"web_new_key|{tg_id}:{tariff_id}"` |
| `BaseRepository[T]` | `database/base.py` | Референс для паттерна, но пишем тонкие asyncpg-репо |

---

## Файловая структура

```
vpn-web-backend/
├── app/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── auth.py           # POST /api/v1/auth/*
│   │   ├── keys.py           # GET/POST/DELETE /api/v1/keys/*
│   │   ├── tariffs.py        # GET /api/v1/tariffs/*
│   │   ├── payments.py       # POST /api/v1/payments/*
│   │   └── admin.py          # /api/v1/admin/*
│   ├── repositories/
│   │   ├── web_users.py      # web_users (email+пароль) — новая таблица
│   │   ├── magic_tokens.py   # magic_tokens — новая таблица
│   │   ├── users.py          # Чтение таблицы users бота
│   │   ├── keys.py           # CRUD таблицы keys бота
│   │   ├── tariffs.py        # Чтение таблицы tariff бота
│   │   └── payments.py       # CRUD таблицы payments бота
│   ├── services/
│   │   ├── auth.py           # Логика входа, JWT, magic link
│   │   ├── keys.py           # Создание/удаление через py3xui
│   │   ├── tariffs.py        # Получение тарифов
│   │   ├── payments.py       # YooKassa + webhook
│   │   └── admin.py          # Враппер DashboardMetricsService + управление
│   ├── schemas/
│   │   ├── auth.py
│   │   ├── keys.py
│   │   ├── tariffs.py
│   │   ├── payments.py
│   │   └── admin.py
│   ├── core/
│   │   ├── config.py         # Settings (pydantic-settings)
│   │   ├── database.py       # asyncpg pool lifecycle
│   │   ├── security.py       # JWT, bcrypt
│   │   ├── xui.py            # py3xui.AsyncApi singleton
│   │   └── dependencies.py   # get_conn, get_current_user, require_admin
│   └── main.py
├── migrations/
│   └── 001_web_auth.sql      # ТОЛЬКО web_users и magic_tokens
├── tests/
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_keys.py
│   ├── test_tariffs.py
│   ├── test_payments.py
│   └── test_admin.py
├── .env.example
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

---

## Task 1: Репозиторий и скаффолдинг проекта

**Files:**
- Create: `requirements.txt`, `app/main.py`, `app/core/config.py`
- Create: `app/core/database.py`, `app/core/xui.py`
- Create: `.env.example`, `Dockerfile`, `docker-compose.yml`
- Create: все `__init__.py` и заглушки роутеров

- [ ] **Step 1: Создать репозиторий и клонировать**

```bash
export PATH="$HOME/.local/bin:$PATH"
gh repo create vpn-web-backend --private --clone
cd /home/claude/vpn-web-backend
git config user.email "egorov@vpnbot.dev"
git config user.name "Egorov3008"
```

- [ ] **Step 2: Создать `requirements.txt`**

```
fastapi==0.115.0
uvicorn[standard]==0.30.6
asyncpg==0.29.0
pydantic==2.9.2
pydantic-settings==2.5.2
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
httpx==0.27.2
py3xui==0.3.3
yookassa==3.3.0
python-dotenv==1.0.1
pytest==8.3.3
pytest-asyncio==0.24.0
```

- [ ] **Step 3: Создать `app/core/config.py`**

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
    yookassa_shop_id: str
    yookassa_secret_key: str
    xui_api_url: str          # https://host:port
    xui_login: str
    xui_password: str
    xui_inbound_id: int = 1   # ID inbound на 3x-UI сервере
    admin_tg_ids: list[int] = []
    magic_token_ttl_minutes: int = 10
    webhook_base_url: str     # https://web.example.com
    disable_webhook_ip_check: bool = False


settings = Settings()
```

- [ ] **Step 4: Создать `app/core/database.py`**

```python
import asyncpg
from app.core.config import settings

_pool: asyncpg.Pool | None = None


async def create_pool() -> asyncpg.Pool:
    global _pool
    _pool = await asyncpg.create_pool(dsn=settings.database_url, min_size=2, max_size=10)
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


def get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("Database pool is not initialized")
    return _pool
```

- [ ] **Step 5: Создать `app/core/xui.py`**

```python
from py3xui import AsyncApi
from app.core.config import settings

_xui_client: AsyncApi | None = None


async def get_xui_client() -> AsyncApi:
    """Возвращает авторизованный клиент py3xui."""
    global _xui_client
    if _xui_client is None:
        _xui_client = AsyncApi(
            host=settings.xui_api_url,
            username=settings.xui_login,
            password=settings.xui_password,
        )
        await _xui_client.login()
    return _xui_client


async def reset_xui_client() -> None:
    global _xui_client
    _xui_client = None
```

- [ ] **Step 6: Создать `app/main.py`**

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.database import create_pool, close_pool
from app.api import auth, keys, tariffs, payments, admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_pool()
    yield
    await close_pool()


app = FastAPI(title="VPN Web Backend", version="1.0.0", lifespan=lifespan)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(keys.router, prefix="/api/v1/keys", tags=["keys"])
app.include_router(tariffs.router, prefix="/api/v1/tariffs", tags=["tariffs"])
app.include_router(payments.router, prefix="/api/v1/payments", tags=["payments"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])


@app.get("/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 7: Создать `.env.example`**

```env
DATABASE_URL=postgresql://user:password@localhost:5432/vpndb
SECRET_KEY=change-me-in-production
TELEGRAM_BOT_TOKEN=123456:ABC-DEF
YOOKASSA_SHOP_ID=12345
YOOKASSA_SECRET_KEY=test_secret
XUI_API_URL=https://your-server.com:2096
XUI_LOGIN=admin
XUI_PASSWORD=password
XUI_INBOUND_ID=1
WEBHOOK_BASE_URL=https://web.example.com
ADMIN_TG_IDS=[]
DISABLE_WEBHOOK_IP_CHECK=false
```

- [ ] **Step 8: Создать `Dockerfile` и `docker-compose.yml`**

```dockerfile
# Dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml
services:
  web:
    build: .
    ports:
      - "8000:8000"
    env_file: .env
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

- [ ] **Step 9: Создать все `__init__.py` и stub-роутеры**

```bash
mkdir -p app/api app/repositories app/services app/schemas app/core tests migrations
touch app/__init__.py app/api/__init__.py app/repositories/__init__.py
touch app/services/__init__.py app/schemas/__init__.py app/core/__init__.py
```

Каждый stub-роутер (`app/api/auth.py`, `keys.py`, `tariffs.py`, `payments.py`, `admin.py`):
```python
from fastapi import APIRouter
router = APIRouter()
```

- [ ] **Step 10: Проверить что приложение импортируется**

```bash
pip install -r requirements.txt
# Минимальный .env для теста импорта:
cat > .env << 'EOF'
DATABASE_URL=postgresql://u:p@localhost/db
SECRET_KEY=test-secret
TELEGRAM_BOT_TOKEN=123:test
YOOKASSA_SHOP_ID=test
YOOKASSA_SECRET_KEY=test
XUI_API_URL=http://localhost
XUI_LOGIN=admin
XUI_PASSWORD=admin
WEBHOOK_BASE_URL=http://localhost
ADMIN_TG_IDS=[]
EOF
python -c "from app.main import app; print('OK')"
```

Ожидается: `OK`

- [ ] **Step 11: Commit**

```bash
git add .
git commit -m "feat: project scaffold — FastAPI app, config, DB pool, XUI client"
git push origin main
```

---

## Task 2: SQL миграция — web_users и magic_tokens

**Files:**
- Create: `migrations/001_web_auth.sql`

> ⚠️ Основная схема БД уже существует (`assets/schema.sql` в боте). Мигрируем ТОЛЬКО новые таблицы.

- [ ] **Step 1: Создать `migrations/001_web_auth.sql`**

```sql
-- Веб-пользователи: email + пароль, необязательная привязка к tg_id
CREATE TABLE IF NOT EXISTS web_users (
    id          SERIAL PRIMARY KEY,
    email       TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    tg_id       BIGINT UNIQUE REFERENCES users(tg_id) ON DELETE SET NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Одноразовые токены для входа через Telegram
CREATE TABLE IF NOT EXISTS magic_tokens (
    token       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tg_id       BIGINT NOT NULL REFERENCES users(tg_id) ON DELETE CASCADE,
    expires_at  TIMESTAMPTZ NOT NULL,
    used        BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_magic_tokens_tg_id ON magic_tokens(tg_id);
CREATE INDEX IF NOT EXISTS idx_magic_tokens_expires ON magic_tokens(expires_at);
```

- [ ] **Step 2: Применить миграцию к существующей БД**

```bash
psql $DATABASE_URL -f migrations/001_web_auth.sql
```

Ожидается: `CREATE TABLE`, `CREATE TABLE`, `CREATE INDEX`, `CREATE INDEX`

- [ ] **Step 3: Commit**

```bash
git add migrations/001_web_auth.sql
git commit -m "feat: add web_users and magic_tokens tables"
```

---

## Task 3: Core security — JWT и bcrypt

**Files:**
- Create: `app/core/security.py`
- Create: `tests/test_security.py`

- [ ] **Step 1: Написать тест**

```python
# tests/test_security.py
import pytest
from datetime import timedelta
from app.core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    decode_token, create_token,
)


def test_password_hash_and_verify():
    hashed = hash_password("mysecret")
    assert verify_password("mysecret", hashed) is True
    assert verify_password("wrong", hashed) is False


def test_create_and_decode_access_token():
    payload = {"sub": "42", "tg_id": 123, "is_admin": False}
    token = create_access_token(payload)
    decoded = decode_token(token)
    assert decoded["sub"] == "42"
    assert decoded["tg_id"] == 123
    assert decoded["is_admin"] is False


def test_expired_token_raises():
    token = create_token({"sub": "1"}, expires_delta=timedelta(seconds=-1))
    with pytest.raises(ValueError):
        decode_token(token)
```

- [ ] **Step 2: Запустить тест — убедиться что падает**

```bash
pytest tests/test_security.py -v
```

Ожидается: `ImportError` или `ModuleNotFoundError`

- [ ] **Step 3: Создать `app/core/security.py`**

```python
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from jose import JWTError, jwt
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


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
```

- [ ] **Step 4: Запустить тест — убедиться что проходит**

```bash
pytest tests/test_security.py -v
```

Ожидается: все 3 теста PASS

- [ ] **Step 5: Commit**

```bash
git add app/core/security.py tests/test_security.py
git commit -m "feat: JWT and bcrypt security utilities"
```

---

## Task 4: Dependencies — get_conn, get_current_user, require_admin

**Files:**
- Create: `app/core/dependencies.py`

- [ ] **Step 1: Создать `app/core/dependencies.py`**

```python
from typing import AsyncGenerator
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import asyncpg
from app.core.database import get_pool
from app.core.security import decode_token

bearer_scheme = HTTPBearer()


async def get_conn() -> AsyncGenerator[asyncpg.Connection, None]:
    pool = get_pool()
    async with pool.acquire() as conn:
        yield conn


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    token = credentials.credentials
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

- [ ] **Step 2: Commit**

```bash
git add app/core/dependencies.py
git commit -m "feat: FastAPI dependencies — DB conn, JWT auth, admin guard"
```

---

## Task 5: Репозитории — web_users, magic_tokens и основные таблицы бота

**Files:**
- Create: `app/repositories/web_users.py`
- Create: `app/repositories/magic_tokens.py`
- Create: `app/repositories/users.py`
- Create: `app/repositories/keys.py`
- Create: `app/repositories/tariffs.py`
- Create: `app/repositories/payments.py`
- Create: `tests/conftest.py`
- Create: `tests/test_repositories.py`

- [ ] **Step 1: Создать `tests/conftest.py`**

```python
import asyncio
import pytest
import asyncpg
from app.core.config import settings


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def db_pool():
    pool = await asyncpg.create_pool(dsn=settings.database_url)
    yield pool
    await pool.close()


@pytest.fixture
async def conn(db_pool):
    async with db_pool.acquire() as connection:
        tr = connection.transaction()
        await tr.start()
        yield connection
        await tr.rollback()
```

- [ ] **Step 2: Написать тесты репозиториев**

```python
# tests/test_repositories.py
import pytest
from app.repositories.web_users import WebUsersRepo
from app.repositories.magic_tokens import MagicTokensRepo
from app.repositories.tariffs import TariffsRepo


@pytest.mark.asyncio
async def test_create_and_get_web_user(conn):
    repo = WebUsersRepo()
    user = await repo.create(conn, email="repotest@example.com", password_hash="hash", tg_id=None)
    assert user["email"] == "repotest@example.com"
    found = await repo.get_by_email(conn, "repotest@example.com")
    assert found is not None and found["id"] == user["id"]


@pytest.mark.asyncio
async def test_get_web_user_not_found(conn):
    repo = WebUsersRepo()
    assert await repo.get_by_email(conn, "ghost@example.com") is None


@pytest.mark.asyncio
async def test_create_and_verify_magic_token(conn):
    # Нужен существующий tg_id в таблице users — пропускаем если нет
    repo = MagicTokensRepo()
    from app.repositories.users import UsersRepo
    users = await UsersRepo().get_all(conn, limit=1)
    if not users:
        pytest.skip("No users in DB")
    tg_id = users[0]["tg_id"]
    token = await repo.create(conn, tg_id=tg_id, ttl_minutes=10)
    record = await repo.get_valid(conn, token)
    assert record is not None and record["tg_id"] == tg_id
    await repo.mark_used(conn, token)
    assert await repo.get_valid(conn, token) is None


@pytest.mark.asyncio
async def test_get_tariffs(conn):
    repo = TariffsRepo()
    tariffs = await repo.get_all(conn)
    assert isinstance(tariffs, list)
```

- [ ] **Step 3: Запустить тесты — убедиться что падают**

```bash
pytest tests/test_repositories.py -v
```

Ожидается: `ImportError`

- [ ] **Step 4: Создать `app/repositories/web_users.py`**

```python
import asyncpg
from typing import Optional


class WebUsersRepo:
    async def create(
        self, conn: asyncpg.Connection, email: str, password_hash: str, tg_id: Optional[int]
    ) -> asyncpg.Record:
        return await conn.fetchrow(
            "INSERT INTO web_users (email, password_hash, tg_id) VALUES ($1, $2, $3) RETURNING *",
            email, password_hash, tg_id,
        )

    async def get_by_email(self, conn: asyncpg.Connection, email: str) -> Optional[asyncpg.Record]:
        return await conn.fetchrow("SELECT * FROM web_users WHERE email = $1", email)

    async def get_by_tg_id(self, conn: asyncpg.Connection, tg_id: int) -> Optional[asyncpg.Record]:
        return await conn.fetchrow("SELECT * FROM web_users WHERE tg_id = $1", tg_id)

    async def link_tg_id(self, conn: asyncpg.Connection, user_id: int, tg_id: int) -> None:
        await conn.execute("UPDATE web_users SET tg_id = $1 WHERE id = $2", tg_id, user_id)
```

- [ ] **Step 5: Создать `app/repositories/magic_tokens.py`**

```python
import asyncpg
from datetime import datetime, timedelta, timezone
from typing import Optional


class MagicTokensRepo:
    async def create(self, conn: asyncpg.Connection, tg_id: int, ttl_minutes: int) -> str:
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)
        row = await conn.fetchrow(
            "INSERT INTO magic_tokens (tg_id, expires_at) VALUES ($1, $2) RETURNING token::text",
            tg_id, expires_at,
        )
        return row["token"]

    async def get_valid(self, conn: asyncpg.Connection, token: str) -> Optional[asyncpg.Record]:
        return await conn.fetchrow(
            "SELECT * FROM magic_tokens WHERE token = $1::uuid AND used = FALSE AND expires_at > NOW()",
            token,
        )

    async def mark_used(self, conn: asyncpg.Connection, token: str) -> None:
        await conn.execute(
            "UPDATE magic_tokens SET used = TRUE WHERE token = $1::uuid", token
        )
```

- [ ] **Step 6: Создать `app/repositories/users.py`**

```python
import asyncpg
from typing import Optional


class UsersRepo:
    async def get_by_tg_id(self, conn: asyncpg.Connection, tg_id: int) -> Optional[asyncpg.Record]:
        return await conn.fetchrow("SELECT * FROM users WHERE tg_id = $1", tg_id)

    async def get_all(self, conn: asyncpg.Connection, limit: int = 50, offset: int = 0) -> list[asyncpg.Record]:
        return await conn.fetch(
            "SELECT * FROM users ORDER BY created_at DESC LIMIT $1 OFFSET $2", limit, offset
        )

    async def search(self, conn: asyncpg.Connection, query: str) -> list[asyncpg.Record]:
        return await conn.fetch(
            "SELECT * FROM users WHERE username ILIKE $1 OR tg_id::text = $2 LIMIT 50",
            f"%{query}%", query,
        )

    async def count(self, conn: asyncpg.Connection) -> int:
        return await conn.fetchval("SELECT COUNT(*) FROM users")

    async def count_today(self, conn: asyncpg.Connection) -> int:
        return await conn.fetchval(
            "SELECT COUNT(*) FROM users WHERE created_at::date = CURRENT_DATE"
        )

    async def set_blocked(self, conn: asyncpg.Connection, tg_id: int, is_blocked: bool) -> None:
        await conn.execute("UPDATE users SET is_blocked = $1 WHERE tg_id = $2", is_blocked, tg_id)

    async def set_admin(self, conn: asyncpg.Connection, tg_id: int, is_admin: bool) -> None:
        await conn.execute("UPDATE users SET is_admin = $1 WHERE tg_id = $2", is_admin, tg_id)
```

- [ ] **Step 7: Создать `app/repositories/keys.py`**

```python
import asyncpg
from typing import Optional


class KeysRepo:
    async def get_by_tg_id(self, conn: asyncpg.Connection, tg_id: int) -> list[asyncpg.Record]:
        return await conn.fetch(
            "SELECT * FROM keys WHERE tg_id = $1 ORDER BY created_at DESC", tg_id
        )

    async def get_by_client_id(self, conn: asyncpg.Connection, client_id: str) -> Optional[asyncpg.Record]:
        return await conn.fetchrow("SELECT * FROM keys WHERE client_id = $1", client_id)

    async def get_all(self, conn: asyncpg.Connection, limit: int = 50, offset: int = 0) -> list[asyncpg.Record]:
        return await conn.fetch(
            "SELECT k.*, u.username FROM keys k LEFT JOIN users u ON k.tg_id = u.tg_id "
            "ORDER BY k.created_at DESC LIMIT $1 OFFSET $2",
            limit, offset,
        )

    async def count_active(self, conn: asyncpg.Connection) -> int:
        return await conn.fetchval(
            "SELECT COUNT(*) FROM keys WHERE expiry_time > EXTRACT(EPOCH FROM NOW()) * 1000"
        )

    async def count_expiring_soon(self, conn: asyncpg.Connection) -> int:
        return await conn.fetchval(
            "SELECT COUNT(*) FROM keys WHERE expiry_time > EXTRACT(EPOCH FROM NOW()) * 1000 "
            "AND expiry_time < EXTRACT(EPOCH FROM (NOW() + INTERVAL '24 hours')) * 1000"
        )

    async def store(
        self, conn: asyncpg.Connection, tg_id: int, client_id: str, email: str,
        expiry_time: int, key: str, inbound_id: int, tariff_id: int,
        total_gb: float = 0.0, reset_date: int = 0
    ) -> asyncpg.Record:
        import time
        created_at = int(time.time() * 1000)
        return await conn.fetchrow(
            """
            INSERT INTO keys
                (tg_id, client_id, email, expiry_time, key, inbound_id, tariff_id, total_gb, reset_date, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            RETURNING *
            """,
            tg_id, client_id, email, expiry_time, key, inbound_id, tariff_id, total_gb, reset_date, created_at,
        )

    async def delete(self, conn: asyncpg.Connection, client_id: str) -> None:
        await conn.execute("DELETE FROM keys WHERE client_id = $1", client_id)

    async def update_expiry(
        self, conn: asyncpg.Connection, client_id: str,
        new_expiry_time: int, tariff_id: int, total_gb: float
    ) -> None:
        await conn.execute(
            "UPDATE keys SET expiry_time = $2, tariff_id = $3, total_gb = $4, "
            "notified_10h = FALSE, notified_24h = FALSE WHERE client_id = $1",
            client_id, new_expiry_time, tariff_id, total_gb,
        )
```

- [ ] **Step 8: Создать `app/repositories/tariffs.py`**

```python
import asyncpg
from typing import Optional

# Таблица называется 'tariff' (не 'tariffs') — из assets/schema.sql бота


class TariffsRepo:
    async def get_all(self, conn: asyncpg.Connection) -> list[asyncpg.Record]:
        return await conn.fetch("SELECT * FROM tariff ORDER BY amount")

    async def get_by_id(self, conn: asyncpg.Connection, tariff_id: int) -> Optional[asyncpg.Record]:
        return await conn.fetchrow("SELECT * FROM tariff WHERE id = $1", tariff_id)
```

- [ ] **Step 9: Создать `app/repositories/payments.py`**

```python
import asyncpg
from typing import Optional


class PaymentsRepo:
    async def create(
        self, conn: asyncpg.Connection, payment_id: str, tg_id: int,
        amount: float, payment_type: str, number_of_months: int = 1,
        discount_percent: int = 0, status: str = "pending"
    ) -> asyncpg.Record:
        return await conn.fetchrow(
            """
            INSERT INTO payments
                (payment_id, tg_id, amount, payment_type, number_of_months, discount_percent, status)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING *
            """,
            payment_id, tg_id, amount, payment_type, number_of_months, discount_percent, status,
        )

    async def get_by_payment_id(self, conn: asyncpg.Connection, payment_id: str) -> Optional[asyncpg.Record]:
        return await conn.fetchrow("SELECT * FROM payments WHERE payment_id = $1", payment_id)

    async def update_status(self, conn: asyncpg.Connection, payment_id: str, status: str) -> None:
        await conn.execute("UPDATE payments SET status = $1 WHERE payment_id = $2", status, payment_id)

    async def revenue_month(self, conn: asyncpg.Connection) -> float:
        return float(await conn.fetchval(
            "SELECT COALESCE(SUM(amount), 0) FROM payments "
            "WHERE status = 'succeeded' AND date_trunc('month', created_at) = date_trunc('month', NOW())"
        ))

    async def revenue_today(self, conn: asyncpg.Connection) -> float:
        return float(await conn.fetchval(
            "SELECT COALESCE(SUM(amount), 0) FROM payments "
            "WHERE status = 'succeeded' AND created_at::date = CURRENT_DATE"
        ))
```

- [ ] **Step 10: Запустить тесты**

```bash
pytest tests/test_repositories.py -v
```

Ожидается: все 4 теста PASS (или skip если нет данных в БД)

- [ ] **Step 11: Commit**

```bash
git add app/repositories/ tests/
git commit -m "feat: all repositories — web_users, magic_tokens, users, keys, tariff, payments"
```

---

## Task 6: Auth — Email + пароль и Telegram magic link

**Files:**
- Create: `app/schemas/auth.py`
- Create: `app/services/auth.py`
- Modify: `app/api/auth.py`
- Create: `tests/test_auth.py`

- [ ] **Step 1: Создать `app/schemas/auth.py`**

```python
from pydantic import BaseModel, EmailStr
from typing import Optional


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    tg_id: Optional[int] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TelegramLoginRequest(BaseModel):
    tg_id: int


class TelegramVerifyRequest(BaseModel):
    token: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
```

- [ ] **Step 2: Создать `app/services/auth.py`**

```python
import secrets
import asyncpg
import httpx
from fastapi import HTTPException, status
from app.repositories.web_users import WebUsersRepo
from app.repositories.magic_tokens import MagicTokensRepo
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from app.core.config import settings

web_users_repo = WebUsersRepo()
magic_tokens_repo = MagicTokensRepo()


def _is_admin(tg_id: int | None) -> bool:
    return tg_id in settings.admin_tg_ids if tg_id else False


def _build_tokens(user_id: int, tg_id: int | None) -> dict:
    payload = {"sub": str(user_id), "tg_id": tg_id, "is_admin": _is_admin(tg_id)}
    return {
        "access_token": create_access_token(payload),
        "refresh_token": create_refresh_token(payload),
        "token_type": "bearer",
    }


async def register(conn: asyncpg.Connection, email: str, password: str, tg_id: int | None) -> dict:
    if await web_users_repo.get_by_email(conn, email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    user = await web_users_repo.create(conn, email=email, password_hash=hash_password(password), tg_id=tg_id)
    return _build_tokens(user["id"], tg_id)


async def login(conn: asyncpg.Connection, email: str, password: str) -> dict:
    user = await web_users_repo.get_by_email(conn, email)
    if not user or not verify_password(password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return _build_tokens(user["id"], user["tg_id"])


async def request_magic_link(conn: asyncpg.Connection, tg_id: int) -> None:
    token = await magic_tokens_repo.create(
        conn, tg_id=tg_id, ttl_minutes=settings.magic_token_ttl_minutes
    )
    url = f"{settings.webhook_base_url}/auth?token={token}"
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
            json={"chat_id": tg_id, "text": f"Ваша ссылка для входа:\n{url}\n\nДействительна 10 минут."},
            timeout=10,
        )
        resp.raise_for_status()


async def verify_magic_token(conn: asyncpg.Connection, token: str) -> dict:
    record = await magic_tokens_repo.get_valid(conn, token)
    if not record:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token invalid or expired")
    await magic_tokens_repo.mark_used(conn, token)
    tg_id = record["tg_id"]

    user = await web_users_repo.get_by_tg_id(conn, tg_id)
    if not user:
        dummy_email = f"tg_{tg_id}@telegram.local"
        user = await web_users_repo.create(
            conn, email=dummy_email, password_hash=hash_password(secrets.token_hex(32)), tg_id=tg_id
        )
    return _build_tokens(user["id"], tg_id)


async def refresh_tokens(refresh_token: str) -> dict:
    try:
        payload = decode_token(refresh_token)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    new_payload = {"sub": payload["sub"], "tg_id": payload.get("tg_id"), "is_admin": payload.get("is_admin", False)}
    return {
        "access_token": create_access_token(new_payload),
        "refresh_token": create_refresh_token(new_payload),
        "token_type": "bearer",
    }
```

- [ ] **Step 3: Написать тесты**

```python
# tests/test_auth.py
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_register(client):
    resp = await client.post("/api/v1/auth/register", json={
        "email": "newuser_auth@example.com", "password": "strongpass123"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data and "refresh_token" in data


@pytest.mark.asyncio
async def test_register_duplicate(client):
    payload = {"email": "dup_auth@example.com", "password": "pass"}
    await client.post("/api/v1/auth/register", json=payload)
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_login_success(client):
    await client.post("/api/v1/auth/register", json={"email": "login_auth@example.com", "password": "mypass"})
    resp = await client.post("/api/v1/auth/login", json={"email": "login_auth@example.com", "password": "mypass"})
    assert resp.status_code == 200 and "access_token" in resp.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    await client.post("/api/v1/auth/register", json={"email": "wp_auth@example.com", "password": "correct"})
    resp = await client.post("/api/v1/auth/login", json={"email": "wp_auth@example.com", "password": "wrong"})
    assert resp.status_code == 401
```

- [ ] **Step 4: Заполнить `app/api/auth.py`**

```python
from fastapi import APIRouter, Depends
import asyncpg
from app.core.dependencies import get_conn
from app.schemas.auth import (
    RegisterRequest, LoginRequest, TokenResponse,
    TelegramLoginRequest, TelegramVerifyRequest, RefreshRequest,
)
from app.services import auth as auth_service

router = APIRouter()


@router.post("/register", response_model=TokenResponse)
async def register(body: RegisterRequest, conn: asyncpg.Connection = Depends(get_conn)):
    return await auth_service.register(conn, body.email, body.password, body.tg_id)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, conn: asyncpg.Connection = Depends(get_conn)):
    return await auth_service.login(conn, body.email, body.password)


@router.post("/telegram/request")
async def telegram_request(body: TelegramLoginRequest, conn: asyncpg.Connection = Depends(get_conn)):
    await auth_service.request_magic_link(conn, body.tg_id)
    return {"message": "Magic link sent to Telegram"}


@router.post("/telegram/verify", response_model=TokenResponse)
async def telegram_verify(body: TelegramVerifyRequest, conn: asyncpg.Connection = Depends(get_conn)):
    return await auth_service.verify_magic_token(conn, body.token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest):
    return await auth_service.refresh_tokens(body.refresh_token)
```

- [ ] **Step 5: Запустить тесты**

```bash
pytest tests/test_auth.py -v
```

Ожидается: все 4 теста PASS

- [ ] **Step 6: Commit**

```bash
git add app/schemas/auth.py app/services/auth.py app/api/auth.py tests/test_auth.py
git commit -m "feat: auth endpoints — register, login, telegram magic link, refresh"
```

---

## Task 7: Тарифы

**Files:**
- Create: `app/schemas/tariffs.py`
- Create: `app/services/tariffs.py`
- Modify: `app/api/tariffs.py`
- Create: `tests/test_tariffs.py`

- [ ] **Step 1: Создать `app/schemas/tariffs.py`**

```python
from pydantic import BaseModel
from typing import Optional


class TariffResponse(BaseModel):
    id: int
    name_tariff: str
    amount: float
    description: Optional[str]
    limit_ip: int
    period: int
    traffic_limit: float
```

- [ ] **Step 2: Создать `app/services/tariffs.py`**

```python
import asyncpg
from fastapi import HTTPException, status
from app.repositories.tariffs import TariffsRepo

tariffs_repo = TariffsRepo()


async def get_all(conn: asyncpg.Connection) -> list[dict]:
    return [dict(r) for r in await tariffs_repo.get_all(conn)]


async def get_by_id(conn: asyncpg.Connection, tariff_id: int) -> dict:
    row = await tariffs_repo.get_by_id(conn, tariff_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tariff not found")
    return dict(row)
```

- [ ] **Step 3: Написать тест**

```python
# tests/test_tariffs.py
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_get_tariffs_public(client):
    resp = await client.get("/api/v1/tariffs/")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_get_tariff_by_id_not_found(client):
    resp = await client.get("/api/v1/tariffs/999999")
    assert resp.status_code == 404
```

- [ ] **Step 4: Заполнить `app/api/tariffs.py`**

```python
from fastapi import APIRouter, Depends
import asyncpg
from app.core.dependencies import get_conn
from app.schemas.tariffs import TariffResponse
from app.services import tariffs as tariff_service

router = APIRouter()


@router.get("/", response_model=list[TariffResponse])
async def list_tariffs(conn: asyncpg.Connection = Depends(get_conn)):
    return await tariff_service.get_all(conn)


@router.get("/{tariff_id}", response_model=TariffResponse)
async def get_tariff(tariff_id: int, conn: asyncpg.Connection = Depends(get_conn)):
    return await tariff_service.get_by_id(conn, tariff_id)
```

- [ ] **Step 5: Запустить тесты**

```bash
pytest tests/test_tariffs.py -v
```

Ожидается: оба PASS

- [ ] **Step 6: Commit**

```bash
git add app/schemas/tariffs.py app/services/tariffs.py app/api/tariffs.py tests/test_tariffs.py
git commit -m "feat: tariffs endpoints"
```

---

## Task 8: Ключи — управление через py3xui

**Files:**
- Create: `app/schemas/keys.py`
- Create: `app/services/keys.py`
- Modify: `app/api/keys.py`
- Create: `tests/test_keys.py`

> **Примечание:** Используем `py3xui.AsyncApi` напрямую (не `XUISession` из бота — тот тащит весь DI с кэшем). `ExpiryCalculator` и `FormationKey` из бота зависят от `ServiceDataModel`/`CacheService` — слишком тяжело для веба. Логику создания ключа реализуем самостоятельно (она проста).

- [ ] **Step 1: Создать `app/schemas/keys.py`**

```python
from pydantic import BaseModel
from typing import Optional


class KeyResponse(BaseModel):
    client_id: str
    email: str
    key: str
    expiry_time: int
    tariff_id: Optional[int]
    name_tariff: Optional[str]
    amount: Optional[float]
    period: Optional[int]
    used_traffic: Optional[float]
    total_gb: Optional[float]


class CreateKeyRequest(BaseModel):
    tariff_id: int


class RenewKeyRequest(BaseModel):
    tariff_id: int
```

- [ ] **Step 2: Создать `app/services/keys.py`**

```python
import uuid
import asyncpg
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status
from py3xui import AsyncApi, Client
from app.repositories.keys import KeysRepo
from app.repositories.tariffs import TariffsRepo
from app.core.config import settings
from app.core.xui import get_xui_client

keys_repo = KeysRepo()
tariffs_repo = TariffsRepo()


def _expiry_ms(period_days: int, months: int = 1) -> int:
    """Вычисляет время истечения ключа в миллисекундах (epoch)."""
    total_days = period_days * months
    expiry_dt = datetime.now(timezone.utc) + timedelta(days=total_days)
    return int(expiry_dt.timestamp() * 1000)


def _random_email() -> str:
    """Генерирует уникальный email-идентификатор ключа."""
    return f"web_{uuid.uuid4().hex[:12]}"


async def _xui_add_client(
    api: AsyncApi, client_id: str, email: str,
    expiry_ms: int, total_gb: int, limit_ip: int,
) -> None:
    """Добавляет клиента в 3x-UI."""
    client = Client(
        id=client_id,
        email=email,
        expiry_time=expiry_ms,
        total_gb=total_gb,
        limit_ip=limit_ip,
        enable=True,
    )
    await api.client.add(inbound_id=settings.xui_inbound_id, clients=[client])


async def _xui_delete_client(api: AsyncApi, client_id: str) -> None:
    await api.client.delete(inbound_id=settings.xui_inbound_id, client_uuid=client_id)


async def _xui_update_client(
    api: AsyncApi, client_id: str, email: str,
    expiry_ms: int, total_gb: int, limit_ip: int,
) -> None:
    client = Client(
        id=client_id,
        email=email,
        expiry_time=expiry_ms,
        total_gb=total_gb,
        limit_ip=limit_ip,
        enable=True,
    )
    await api.client.update(client_uuid=client_id, client=client)


async def get_user_keys(conn: asyncpg.Connection, tg_id: int) -> list[dict]:
    return [dict(r) for r in await keys_repo.get_by_tg_id(conn, tg_id)]


async def create_key(conn: asyncpg.Connection, tg_id: int, tariff_id: int) -> dict:
    tariff = await tariffs_repo.get_by_id(conn, tariff_id)
    if not tariff:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tariff not found")

    client_id = str(uuid.uuid4())
    email = _random_email()
    expiry = _expiry_ms(tariff["period"])
    total_gb = int(tariff["traffic_limit"] * (2 ** 30)) if tariff["traffic_limit"] > 0 else 0

    api = await get_xui_client()
    await _xui_add_client(api, client_id, email, expiry, total_gb, tariff["limit_ip"])

    subscription_url = f"{settings.xui_api_url}/sub/{email}"
    row = await keys_repo.store(
        conn, tg_id=tg_id, client_id=client_id, email=email,
        expiry_time=expiry, key=subscription_url,
        inbound_id=settings.xui_inbound_id, tariff_id=tariff_id,
        total_gb=float(total_gb),
    )
    return dict(row)


async def delete_key(conn: asyncpg.Connection, client_id: str, tg_id: int) -> None:
    row = await keys_repo.get_by_client_id(conn, client_id)
    if not row or row["tg_id"] != tg_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Key not found")
    api = await get_xui_client()
    await _xui_delete_client(api, client_id)
    await keys_repo.delete(conn, client_id)


async def renew_key(conn: asyncpg.Connection, client_id: str, tg_id: int, tariff_id: int) -> dict:
    row = await keys_repo.get_by_client_id(conn, client_id)
    if not row or row["tg_id"] != tg_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Key not found")
    tariff = await tariffs_repo.get_by_id(conn, tariff_id)
    if not tariff:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tariff not found")

    new_expiry = _expiry_ms(tariff["period"])
    total_gb = int(tariff["traffic_limit"] * (2 ** 30)) if tariff["traffic_limit"] > 0 else 0

    api = await get_xui_client()
    await _xui_update_client(api, client_id, row["email"], new_expiry, total_gb, tariff["limit_ip"])
    await keys_repo.update_expiry(conn, client_id, new_expiry, tariff_id, float(total_gb))
    return dict(await keys_repo.get_by_client_id(conn, client_id))
```

- [ ] **Step 3: Написать тесты**

```python
# tests/test_keys.py
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
async def auth_headers(client):
    resp = await client.post("/api/v1/auth/register", json={
        "email": "keyuser_test@example.com", "password": "pass123"
    })
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.mark.asyncio
async def test_list_keys_empty(client, auth_headers):
    resp = await client.get("/api/v1/keys/", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_keys_unauthorized(client):
    resp = await client.get("/api/v1/keys/")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_delete_key_not_found(client, auth_headers):
    resp = await client.delete("/api/v1/keys/nonexistent-uuid", headers=auth_headers)
    assert resp.status_code == 404
```

- [ ] **Step 4: Заполнить `app/api/keys.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, status
import asyncpg
from app.core.dependencies import get_conn, get_current_user
from app.schemas.keys import KeyResponse, CreateKeyRequest, RenewKeyRequest
from app.services import keys as keys_service

router = APIRouter()


def _require_tg_id(current_user: dict) -> int:
    tg_id = current_user.get("tg_id")
    if not tg_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Telegram account required to manage keys",
        )
    return tg_id


@router.get("/", response_model=list[KeyResponse])
async def list_keys(
    conn: asyncpg.Connection = Depends(get_conn),
    current_user: dict = Depends(get_current_user),
):
    tg_id = current_user.get("tg_id")
    if not tg_id:
        return []
    return await keys_service.get_user_keys(conn, tg_id)


@router.post("/", response_model=KeyResponse)
async def create_key(
    body: CreateKeyRequest,
    conn: asyncpg.Connection = Depends(get_conn),
    current_user: dict = Depends(get_current_user),
):
    return await keys_service.create_key(conn, _require_tg_id(current_user), body.tariff_id)


@router.get("/{client_id}", response_model=KeyResponse)
async def get_key(
    client_id: str,
    conn: asyncpg.Connection = Depends(get_conn),
    current_user: dict = Depends(get_current_user),
):
    tg_id = _require_tg_id(current_user)
    keys = await keys_service.get_user_keys(conn, tg_id)
    key = next((k for k in keys if k["client_id"] == client_id), None)
    if not key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Key not found")
    return key


@router.post("/{client_id}/renew", response_model=KeyResponse)
async def renew_key(
    client_id: str,
    body: RenewKeyRequest,
    conn: asyncpg.Connection = Depends(get_conn),
    current_user: dict = Depends(get_current_user),
):
    return await keys_service.renew_key(conn, client_id, _require_tg_id(current_user), body.tariff_id)


@router.delete("/{client_id}", status_code=204)
async def delete_key(
    client_id: str,
    conn: asyncpg.Connection = Depends(get_conn),
    current_user: dict = Depends(get_current_user),
):
    await keys_service.delete_key(conn, client_id, _require_tg_id(current_user))
```

- [ ] **Step 5: Запустить тесты**

```bash
pytest tests/test_keys.py -v
```

Ожидается: все 3 теста PASS

- [ ] **Step 6: Commit**

```bash
git add app/schemas/keys.py app/services/keys.py app/api/keys.py tests/test_keys.py
git commit -m "feat: keys endpoints — CRUD + renew via py3xui"
```

---

## Task 9: Платежи — YooKassa + webhook

**Files:**
- Create: `app/schemas/payments.py`
- Create: `app/services/payments.py`
- Modify: `app/api/payments.py`
- Create: `tests/test_payments.py`

> `payment_type` формат: `"web_new_key|{tg_id}:{tariff_id}"` — совместим с паттерном `processor.extract_operation()` бота, операция отделяется `|`. Webhook читает это поле для создания ключа.

- [ ] **Step 1: Создать `app/schemas/payments.py`**

```python
from pydantic import BaseModel


class CreatePaymentRequest(BaseModel):
    tariff_id: int


class PaymentResponse(BaseModel):
    payment_id: str
    payment_url: str
    amount: float
```

- [ ] **Step 2: Создать `app/services/payments.py`**

```python
import asyncio
import asyncpg
import uuid
from fastapi import HTTPException, Request, status
from yookassa import Configuration, Payment
from yookassa.domain.common import SecurityHelper
from yookassa.domain.notification import WebhookNotificationFactory, WebhookNotificationEventType
from app.repositories.payments import PaymentsRepo
from app.repositories.tariffs import TariffsRepo
from app.services.keys import create_key
from app.core.config import settings

Configuration.account_id = settings.yookassa_shop_id
Configuration.secret_key = settings.yookassa_secret_key

payments_repo = PaymentsRepo()
tariffs_repo = TariffsRepo()

# payment_type формат: "web_new_key|{tg_id}:{tariff_id}"
_OPERATION = "web_new_key"


async def create_payment(conn: asyncpg.Connection, tg_id: int, tariff_id: int) -> dict:
    tariff = await tariffs_repo.get_by_id(conn, tariff_id)
    if not tariff:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tariff not found")

    idempotence_key = str(uuid.uuid4())
    payment = await asyncio.to_thread(
        Payment.create,
        {
            "amount": {"value": f"{tariff['amount']:.2f}", "currency": "RUB"},
            "confirmation": {
                "type": "redirect",
                "return_url": f"{settings.webhook_base_url}/payment/success",
            },
            "capture": True,
            "description": f"VPN: {tariff['name_tariff']}",
        },
        idempotence_key,
    )

    payment_type = f"{_OPERATION}|{tg_id}:{tariff_id}"
    await payments_repo.create(
        conn,
        payment_id=payment.id,
        tg_id=tg_id,
        amount=tariff["amount"],
        payment_type=payment_type,
        status="pending",
    )

    return {
        "payment_id": payment.id,
        "payment_url": payment.confirmation.confirmation_url,
        "amount": tariff["amount"],
    }


async def handle_webhook(conn: asyncpg.Connection, body: bytes, request: Request) -> None:
    # Проверка IP YooKassa (можно отключить через DISABLE_WEBHOOK_IP_CHECK=true)
    if not settings.disable_webhook_ip_check:
        ip = request.headers.get("X-Forwarded-For", request.client.host)
        if not SecurityHelper().is_ip_trusted(ip):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Untrusted IP")

    try:
        import json
        event_json = json.loads(body)
        notification = WebhookNotificationFactory().create(event_json)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook payload")

    if notification.event != WebhookNotificationEventType.PAYMENT_SUCCEEDED:
        return

    payment_id = notification.object.id
    existing = await payments_repo.get_by_payment_id(conn, payment_id)
    if not existing or existing["status"] == "succeeded":
        return  # идемпотентность

    await payments_repo.update_status(conn, payment_id, "succeeded")

    # Парсим payment_type: "web_new_key|{tg_id}:{tariff_id}"
    payment_type = existing["payment_type"] or ""
    if "|" not in payment_type:
        return
    operation, data = payment_type.split("|", 1)
    if operation != _OPERATION or ":" not in data:
        return

    tg_id_str, tariff_id_str = data.split(":", 1)
    try:
        tg_id, tariff_id = int(tg_id_str), int(tariff_id_str)
    except ValueError:
        return

    await create_key(conn, tg_id=tg_id, tariff_id=tariff_id)
```

- [ ] **Step 3: Написать тесты**

```python
# tests/test_payments.py
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_create_payment_unauthorized(client):
    resp = await client.post("/api/v1/payments/create", json={"tariff_id": 1})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_webhook_invalid_json(client):
    resp = await client.post("/api/v1/payments/webhook", content=b"not-json")
    assert resp.status_code == 400
```

- [ ] **Step 4: Заполнить `app/api/payments.py`**

```python
from fastapi import APIRouter, Depends, Request
import asyncpg
from app.core.dependencies import get_conn, get_current_user
from app.schemas.payments import CreatePaymentRequest, PaymentResponse
from app.services import payments as payment_service

router = APIRouter()


@router.post("/create", response_model=PaymentResponse)
async def create_payment(
    body: CreatePaymentRequest,
    conn: asyncpg.Connection = Depends(get_conn),
    current_user: dict = Depends(get_current_user),
):
    tg_id = current_user.get("tg_id")
    if not tg_id:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Telegram account required")
    return await payment_service.create_payment(conn, tg_id, body.tariff_id)


@router.post("/webhook")
async def payment_webhook(request: Request, conn: asyncpg.Connection = Depends(get_conn)):
    body = await request.body()
    await payment_service.handle_webhook(conn, body, request)
    return {"status": "ok"}
```

- [ ] **Step 5: Запустить тесты**

```bash
pytest tests/test_payments.py -v
```

Ожидается: оба PASS

- [ ] **Step 6: Commit**

```bash
git add app/schemas/payments.py app/services/payments.py app/api/payments.py tests/test_payments.py
git commit -m "feat: payments — YooKassa create + idempotent webhook handler"
```

---

## Task 10: Админ — DashboardMetricsService + управление пользователями и ключами

**Files:**
- Create: `app/schemas/admin.py`
- Create: `app/services/admin.py`
- Modify: `app/api/admin.py`
- Create: `tests/test_admin.py`

> **Ключевое:** `DashboardMetricsService` из `services/analytics/dashboard_metrics.py` бота принимает только `asyncpg.Pool` — используем напрямую для `/admin/stats`. Он уже считает MRR, воронку, истекающие ключи, конверсию.

- [ ] **Step 1: Скопировать `DashboardMetricsService` из бота**

```bash
# Из директории бота (user_system ветка):
cp /home/claude/Bot_3xui_vpn/services/analytics/dashboard_metrics.py app/services/dashboard_metrics.py
```

Файл `app/services/dashboard_metrics.py` содержит `DashboardMetricsService` — не изменяем, используем как есть. Он не имеет зависимостей от Telegram.

- [ ] **Step 2: Создать `app/schemas/admin.py`**

```python
from pydantic import BaseModel
from typing import Optional


class UserAdminResponse(BaseModel):
    tg_id: int
    username: Optional[str]
    first_name: Optional[str]
    is_admin: bool
    is_blocked: bool
    trial: int
    keys_count: int


class UserPatchRequest(BaseModel):
    is_blocked: Optional[bool] = None
    is_admin: Optional[bool] = None


class AdminCreateKeyRequest(BaseModel):
    tg_id: int
    tariff_id: int
```

- [ ] **Step 3: Создать `app/services/admin.py`**

```python
import asyncpg
from fastapi import HTTPException, status
from app.repositories.users import UsersRepo
from app.repositories.keys import KeysRepo
from app.services.keys import create_key, delete_key as svc_delete_key

users_repo = UsersRepo()
keys_repo = KeysRepo()


async def get_users(conn: asyncpg.Connection, limit: int, offset: int, search: str | None) -> list[dict]:
    rows = await (users_repo.search(conn, search) if search else users_repo.get_all(conn, limit, offset))
    result = []
    for row in rows:
        keys = await keys_repo.get_by_tg_id(conn, row["tg_id"])
        result.append({**dict(row), "keys_count": len(keys)})
    return result


async def get_user(conn: asyncpg.Connection, tg_id: int) -> dict:
    user = await users_repo.get_by_tg_id(conn, tg_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    keys = await keys_repo.get_by_tg_id(conn, tg_id)
    return {**dict(user), "keys": [dict(k) for k in keys]}


async def patch_user(conn: asyncpg.Connection, tg_id: int, is_blocked: bool | None, is_admin: bool | None) -> dict:
    if not await users_repo.get_by_tg_id(conn, tg_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if is_blocked is not None:
        await users_repo.set_blocked(conn, tg_id, is_blocked)
    if is_admin is not None:
        await users_repo.set_admin(conn, tg_id, is_admin)
    return dict(await users_repo.get_by_tg_id(conn, tg_id))


async def get_all_keys(conn: asyncpg.Connection, limit: int, offset: int) -> list[dict]:
    return [dict(r) for r in await keys_repo.get_all(conn, limit, offset)]


async def admin_force_delete_key(conn: asyncpg.Connection, client_id: str) -> None:
    row = await keys_repo.get_by_client_id(conn, client_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Key not found")
    from app.core.xui import get_xui_client
    api = await get_xui_client()
    from app.services.keys import _xui_delete_client
    await _xui_delete_client(api, client_id)
    await keys_repo.delete(conn, client_id)
```

- [ ] **Step 4: Написать тесты**

```python
# tests/test_admin.py
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_stats_requires_admin(client):
    resp = await client.get("/api/v1/admin/stats")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_users_requires_admin(client):
    resp = await client.get("/api/v1/admin/users")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_keys_requires_admin(client):
    resp = await client.get("/api/v1/admin/keys")
    assert resp.status_code == 403
```

- [ ] **Step 5: Заполнить `app/api/admin.py`**

```python
from fastapi import APIRouter, Depends, Query
from typing import Optional
import asyncpg
from app.core.dependencies import get_conn, require_admin
from app.core.database import get_pool
from app.schemas.admin import UserPatchRequest, AdminCreateKeyRequest
from app.services import admin as admin_service
from app.services.keys import create_key
from app.services.dashboard_metrics import DashboardMetricsService

router = APIRouter()


@router.get("/stats")
async def stats(_: dict = Depends(require_admin)):
    pool = get_pool()
    svc = DashboardMetricsService(pool)
    metrics = await svc.get_all_dashboard_metrics()
    return {
        "mrr_current_month": metrics.mrr_current_month,
        "mrr_previous_month": metrics.mrr_previous_month,
        "mrr_growth": metrics.mrr_growth,
        "paying_users_current": metrics.paying_users_current,
        "total_new_users_30d": metrics.total_new_users_30d,
        "conversion_to_keys_pct": metrics.conversion_to_keys_pct,
        "conversion_to_paid_pct": metrics.conversion_to_paid_pct,
        "total_expiring_72h": metrics.total_expiring_72h,
        "total_succeeded": metrics.total_succeeded,
        "succeeded_pct": metrics.succeeded_pct,
    }


@router.get("/users")
async def list_users(
    limit: int = Query(50, le=100),
    offset: int = Query(0),
    search: Optional[str] = Query(None),
    conn: asyncpg.Connection = Depends(get_conn),
    _: dict = Depends(require_admin),
):
    return await admin_service.get_users(conn, limit, offset, search)


@router.get("/users/{tg_id}")
async def get_user(
    tg_id: int,
    conn: asyncpg.Connection = Depends(get_conn),
    _: dict = Depends(require_admin),
):
    return await admin_service.get_user(conn, tg_id)


@router.patch("/users/{tg_id}")
async def patch_user(
    tg_id: int,
    body: UserPatchRequest,
    conn: asyncpg.Connection = Depends(get_conn),
    _: dict = Depends(require_admin),
):
    return await admin_service.patch_user(conn, tg_id, body.is_blocked, body.is_admin)


@router.get("/keys")
async def list_keys(
    limit: int = Query(50, le=100),
    offset: int = Query(0),
    conn: asyncpg.Connection = Depends(get_conn),
    _: dict = Depends(require_admin),
):
    return await admin_service.get_all_keys(conn, limit, offset)


@router.post("/keys")
async def admin_create_key(
    body: AdminCreateKeyRequest,
    conn: asyncpg.Connection = Depends(get_conn),
    _: dict = Depends(require_admin),
):
    return await create_key(conn, body.tg_id, body.tariff_id)


@router.delete("/keys/{client_id}", status_code=204)
async def admin_delete_key(
    client_id: str,
    conn: asyncpg.Connection = Depends(get_conn),
    _: dict = Depends(require_admin),
):
    await admin_service.admin_force_delete_key(conn, client_id)
```

- [ ] **Step 6: Запустить тесты**

```bash
pytest tests/test_admin.py -v
```

Ожидается: все 3 PASS

- [ ] **Step 7: Запустить весь suite**

```bash
pytest tests/ -v
```

Ожидается: все тесты PASS

- [ ] **Step 8: Commit**

```bash
git add app/schemas/admin.py app/services/admin.py app/services/dashboard_metrics.py app/api/admin.py tests/test_admin.py
git commit -m "feat: admin panel — stats via DashboardMetricsService, users and keys management"
```

---

## Task 11: Деплой и финальная проверка

**Files:**
- Verify: OpenAPI docs, все роуты
- Run: полный pytest suite

- [ ] **Step 1: Проверить импорт приложения**

```bash
python -c "from app.main import app; print('App imports OK')"
```

Ожидается: `App imports OK`

- [ ] **Step 2: Запустить полный тест suite**

```bash
pytest tests/ -v --tb=short
```

Ожидается: все тесты PASS

- [ ] **Step 3: Запустить сервер локально и проверить /docs**

```bash
uvicorn app.main:app --reload &
sleep 3
curl http://localhost:8000/health
```

Ожидается: `{"status":"ok"}`

Открыть `http://localhost:8000/docs` и проверить:
- `/api/v1/auth/*` — 5 эндпоинтов
- `/api/v1/keys/*` — 5 эндпоинтов
- `/api/v1/tariffs/*` — 2 эндпоинта
- `/api/v1/payments/*` — 2 эндпоинта
- `/api/v1/admin/*` — 7 эндпоинтов

- [ ] **Step 4: Финальный push**

```bash
git add .
git commit -m "feat: final verification — all endpoints operational"
git push origin main
```
