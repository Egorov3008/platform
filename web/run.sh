#!/bin/bash
set -e

# Wait for postgres to be ready
echo "Waiting for PostgreSQL..."
for i in {1..30}; do
  if python -c "import asyncpg; import asyncio; asyncio.run(asyncpg.connect('${DATABASE_URL}'))" 2>/dev/null; then
    echo "PostgreSQL is ready!"
    break
  fi
  echo "PostgreSQL not ready, waiting... ($i/30)"
  sleep 1
done

# Auto-apply web/migrations/*.sql on startup (idempotent loop).
# Skips files matching *drop* (003_drop_login_codes.sql) — those are one-shot
# dev cleanup migrations not safe to re-run on a partially-migrated DB.
# This block is for FIRST RUN ONLY: the loop applies schema in numerical order,
# and migrations use IF NOT EXISTS / DO $$ guards, so re-running is a no-op.
echo "Applying web migrations..."
MIGRATIONS_DIR="/app/migrations"
if [ -d "$MIGRATIONS_DIR" ]; then
  for f in $(ls "$MIGRATIONS_DIR"/*.sql 2>/dev/null | sort); do
    case "$(basename "$f")" in
      *drop*) echo "  skip (drop migration): $f" ;;
      *)
        echo "  applying: $f"
        if psql "$DATABASE_URL" -v ON_ERROR_STOP=0 -f "$f" >/dev/null 2>&1; then
          echo "    ok"
        else
          echo "    warning: failed to apply (continuing)"
        fi
        ;;
    esac
  done
else
  echo "  no migrations dir at $MIGRATIONS_DIR (skipping)"
fi

# HTTP on 8000 (nginx terminates SSL)
exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
