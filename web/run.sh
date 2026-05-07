#!/bin/bash
exec python -m uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8443 \
    --ssl-keyfile=/certs/localhost.key \
    --ssl-certfile=/certs/localhost.crt
