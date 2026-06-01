<!-- generated-by: gsd-doc-writer -->
# Development

## Local Setup

### Prerequisites

- Python >= 3.11
- PostgreSQL 16
- Node.js (for Playwright E2E tests in `web/`)
- A running 3x-UI panel instance (for integration testing)

### Clone and configure

```bash
git clone <repository-url>
cd vpn-platform
```

Each component has its own `.env` file. Copy and fill in the values from the provided examples:

```bash
# Root-level Docker variables
cp .env.example .env

# Backend
cp backend/.env.example backend/.env

# Web
cp web/.env.example web/.env

# Bot: create bot/.env manually — see bot/.env.example reference below
```

Root `.env` values (`DB_NAME`, `DB_USER`, `DB_PASSWORD`) are used by `docker-compose.yml` only. The per-component `.env` files contain the full DSN.

### Install dependencies

Each component manages its own virtualenv and requirements:

```bash
# Backend
cd backend && pip install -r requirements.txt

# Bot
cd bot && pip install -r requirements.txt

# Web
cd web && pip install -r requirements.txt

# Web E2E (Playwright browsers)
cd web && npx playwright install
```

### Apply database migrations (web auth tables)

Web migrations are auto-applied on container startup by `web/run.sh` (idempotent loop, skips `*drop*` files). For local dev (no Docker), apply manually:

```bash
for f in web/migrations/*.sql; do
  case "$(basename "$f")" in *drop*) continue;; esac
  psql "$DATABASE_URL" -f "$f" || true
done
```

Backend database schema is managed directly; no migration runner is used in `backend/`.

## Running Components

### Full stack (Docker Compose)

```bash
docker-compose up -d
```

Services: `postgres` (5432), `backend` (8000), `web` (8001), `bot` (host network).

### Individual components (development mode)

```bash
# Backend — port 8000
cd backend && uvicorn app.main:app --reload

# Bot
cd bot && python main.py

# Web — port 8001
cd web && uvicorn app.main:app --port 8001 --reload
```

## Build Commands

### Backend

| Command | Description |
|---|---|
| `uvicorn app.main:app --reload` | Run development server on port 8000 |
| `pytest` | Run all backend tests |
| `pytest tests/api/test_keys.py` | Run a single test file |
| `pytest tests/api/test_keys.py::test_list_keys` | Run a single test by name |

### Bot

| Command | Description |
|---|---|
| `python main.py` | Run the bot |
| `make lint` | Run Ruff linter (`ruff check .`) |
| `make formatting` | Auto-fix lint issues and format (`ruff check . --fix && ruff format .`) |
| `make test` | Run all tests (`pytest`) |
| `make test-fast` | Run tests, stop on first failure (`pytest -x --tb=short -q`) |
| `make test-cov` | Run tests with HTML coverage report |
| `make test-module MODULE=<name>` | Run tests for a single module (`pytest tests/<name>/`) |
| `make ci` | Run CI test suite with coverage threshold >= 75% |
| `vulture . --min-confidence 100` | Dead code detection |
| `mypy .` | Type checking |

### Web

| Command | Description |
|---|---|
| `uvicorn app.main:app --port 8001 --reload` | Run development server on port 8001 |
| `pytest` | Run all unit tests |
| `pytest tests/test_auth.py` | Run a single test file |
| `pytest tests/test_auth.py::test_register` | Run a single test by name |
| `npx playwright test` | Run E2E tests (requires running browser) |

## Code Style

### Bot — Ruff

The bot component uses [Ruff](https://docs.astral.sh/ruff/) for both linting and formatting. Configuration is in `bot/pyproject.toml`.

```bash
cd bot
make lint        # check only
make formatting  # auto-fix + format
```

### Backend and Web — no enforced formatter configured

Backend and web components do not have a Ruff or Prettier config file present. Follow the existing code conventions (PEP 8, type hints throughout, async functions for all I/O).

### Shared conventions

- **Language:** Code comments and user-visible messages are in Russian (legacy convention).
- **Async:** All database operations use `asyncpg` and must be `async`.
- **Interfaces:** Use `typing.Protocol` for service boundaries.
- **Logging:** Use `get_logger(__name__)` from each component's `core/logging.py` — never use `print()`.
- **Cache access (bot):** All cache reads and writes must go through `CacheService` attributes (e.g., `cache_service.keys.get(...)`). Never instantiate `ModelCache[T]` directly.
- **Cache identifiers (critical):** `Key` → `email`, `Inbound` → `(server_id, inbound_id)`, `PaymentModel` → `payment_id`. Never use `.id` for these models.

## Architecture Contract

The monorepo enforces a strict layering rule:

- The bot (`bot/`) and web (`web/`) must **never** access the database directly — only via backend HTTP API.
- All business logic (key creation, payment processing, tariff management) lives exclusively in `backend/`.
- YooKassa and 3x-UI integrations are backend-only.
- The web layer is a **stateless API proxy + JWT auth layer**: it maintains only `login_codes`, `web_users`, and `magic_tokens` tables.

### Inter-service authentication

| Client | Header | Value |
|---|---|---|
| Bot → Backend | `X-Bot-Secret` | `BOT_SECRET_KEY` env var |
| Web → Backend | `X-Bot-Secret` | `BOT_SECRET_KEY` env var |
| Web frontend → Web API | JWT in HttpOnly cookie | `access_token` + `refresh_token` |
| Admin → Backend | `X-API-Key` | `ADMIN_API_KEY` env var |

## Branch Conventions

No branch naming convention is documented in the repository. No `.github/` directory or pull request templates exist.

## PR Process

No formal PR process is documented. No `.github/PULL_REQUEST_TEMPLATE.md` exists in the repository.
