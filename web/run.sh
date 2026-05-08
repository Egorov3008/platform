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

# HTTP on 8002 for local dev
python -m uvicorn app.main:app --host 0.0.0.0 --port 8002 &
# HTTPS on 8443
exec python -m uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8443 \
    --ssl-keyfile=/certs/localhost.key \
    --ssl-certfile=/certs/localhost.crt
