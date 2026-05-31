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

# HTTP on 8000 (nginx terminates SSL)
exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
