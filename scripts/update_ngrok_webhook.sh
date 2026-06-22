#!/usr/bin/env bash
set -euo pipefail

# ===================================================================
# Update YooKassa webhook URL when ngrok domain changes.
#
# Usage:
#   1. Start dev backend: make dev-up
#   2. Start ngrok:       ngrok http 8000
#   3. Run this script:   ./scripts/update_ngrok_webhook.sh
#
# The script:
#   - reads the current public HTTPS URL from ngrok API (127.0.0.1:4040)
#   - updates WEBHOOK_BASE_URL in .env.dev
#   - registers the webhook in YooKassa test environment
# ===================================================================

ENV_FILE=".env.dev"
WEBHOOK_PATH="/api/v1/payments/webhook"
NGROK_API="http://127.0.0.1:4040/api/tunnels"

if [[ ! -f "$ENV_FILE" ]]; then
    echo "❌ $ENV_FILE not found. Run from project root."
    exit 1
fi

echo "🔍 Fetching ngrok public URL from $NGROK_API..."
NGROK_URL=$(curl -s "$NGROK_API" | grep -o '"public_url":"https://[^"]*"' | head -1 | sed 's/.*"https:\/\//https:\/\//' | tr -d '"')

if [[ -z "$NGROK_URL" ]]; then
    echo "❌ Could not find ngrok HTTPS URL. Is ngrok running on port 8000?"
    exit 1
fi

WEBHOOK_BASE_URL="${NGROK_URL%/}"  # strip trailing slash
FULL_WEBHOOK_URL="${WEBHOOK_BASE_URL}${WEBHOOK_PATH}"

echo "🌐 ngrok URL:        $WEBHOOK_BASE_URL"
echo "🔗 YooKassa webhook: $FULL_WEBHOOK_URL"

# Update .env.dev WEBHOOK_BASE_URL
if grep -q "^WEBHOOK_BASE_URL=" "$ENV_FILE"; then
    sed -i "s|^WEBHOOK_BASE_URL=.*|WEBHOOK_BASE_URL=$WEBHOOK_BASE_URL|" "$ENV_FILE"
else
    echo "WEBHOOK_BASE_URL=$WEBHOOK_BASE_URL" >> "$ENV_FILE"
fi
echo "✅ Updated $ENV_FILE"

# Load YooKassa credentials from .env.dev
YOOKASSA_SHOP_ID=$(grep "^YOOKASSA_SHOP_ID=" "$ENV_FILE" | cut -d '=' -f2- | tr -d '"')
YOOKASSA_SECRET_KEY=$(grep "^YOOKASSA_SECRET_KEY=" "$ENV_FILE" | cut -d '=' -f2- | tr -d '"')

if [[ -z "$YOOKASSA_SHOP_ID" || "$YOOKASSA_SHOP_ID" == "123456" ]]; then
    echo "⚠️  Set a real YOOKASSA_SHOP_ID in $ENV_FILE before registering webhook."
    exit 1
fi

if [[ -z "$YOOKASSA_SECRET_KEY" || "$YOOKASSA_SECRET_KEY" == test_*x ]]; then
    echo "⚠️  Set a real YOOKASSA_SECRET_KEY in $ENV_FILE before registering webhook."
    exit 1
fi

AUTH=$(printf '%s:%s' "$YOOKASSA_SHOP_ID" "$YOOKASSA_SECRET_KEY" | base64 -w0)
IDEMPOTENCE_KEY=$(cat /proc/sys/kernel/random/uuid 2>/dev/null || python3 -c "import uuid; print(uuid.uuid4())")

echo "📡 Registering webhook in YooKassa..."
RESPONSE=$(curl -s -w "\n%{http_code}" \
    -X POST \
    -H "Content-Type: application/json" \
    -H "Authorization: Basic $AUTH" \
    -H "Idempotence-Key: $IDEMPOTENCE_KEY" \
    -d "{\"event\":\"payment.succeeded\",\"url\":\"$FULL_WEBHOOK_URL\"}" \
    "https://api.yookassa.ru/v3/webhooks")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [[ "$HTTP_CODE" == 200 || "$HTTP_CODE" == 201 ]]; then
    echo "✅ Webhook registered successfully (HTTP $HTTP_CODE)"
    echo "$BODY"
else
    echo "❌ Failed to register webhook (HTTP $HTTP_CODE)"
    echo "$BODY"
    exit 1
fi
