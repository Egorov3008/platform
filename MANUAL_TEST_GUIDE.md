# Manual Testing Guide: Unified Web Auth Flow

## Prerequisites

- Backend running on http://localhost:8000
- Web running on http://localhost:8001
- Both have working PostgreSQL connections

## Start Servers

```bash
# Terminal 1: Backend
cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Web
cd web && uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

## Test 1: New User Login (Auto-Create)

**Scenario:** User not in backend, visits web login, uses Telegram Widget

**Steps:**

1. Choose a new Telegram ID (e.g., 9999999)
2. Verify user doesn't exist:
```bash
curl -s -X GET http://localhost:8000/api/v1/users/9999999 \
  -H "X-Bot-Secret: test_secret"
```
Should return **404 Not Found**

3. Get CAPTCHA token:
```bash
curl -s -X GET http://localhost:8001/api/v1/auth/captcha | jq .
```

4. Get Telegram Widget data (simulated - in real test use actual Widget):
```bash
curl -s -X POST http://localhost:8001/api/v1/auth/telegram-callback \
  -H "Content-Type: application/json" \
  -d '{
    "telegram_data": {
      "id": 9999999,
      "first_name": "NewUser",
      "hash": "valid_hash"
    },
    "captcha_token": "YOUR_TOKEN_FROM_ABOVE",
    "captcha_timestamp": '$(date +%s)',
    "captcha_answer": 2
  }' | jq .
```

**Expected:** 200 OK with `access_token` cookie and `user: {tg_id: 9999999, is_admin: false}`

5. Verify user was created in backend:
```bash
curl -s -X GET http://localhost:8000/api/v1/users/9999999 \
  -H "X-Bot-Secret: test_secret"
```
Should now return **200 OK** with user data

---

## Test 2: Existing User Login (Direct)

**Scenario:** User already in backend (from bot), visits web login

**Steps:**

1. Pick an existing user from backend (or create one manually in database)
2. Use its `tg_id` in the following test (replace 777 with real ID):

```bash
curl -s -X POST http://localhost:8001/api/v1/auth/telegram-callback \
  -H "Content-Type: application/json" \
  -d '{
    "telegram_data": {
      "id": 777,
      "first_name": "ExistingUser",
      "hash": "valid_hash"
    },
    "captcha_token": "YOUR_TOKEN",
    "captcha_timestamp": '$(date +%s)',
    "captcha_answer": 2
  }' | jq .
```

**Expected:** 200 OK with `access_token` cookie and `user: {tg_id: 777, is_admin: ...}`

---

## Test 3: Check JWT Contents

After login (Test 1 or 2), decode the access_token cookie:

```bash
# JWT is in the access_token cookie - decode it (use jwt.io or local decoder)
# Should contain: {"tg_id": <id>, "is_admin": <bool>, ...}
```

---

## Test 4: Use JWT for Subsequent Requests

```bash
# List keys for logged-in user (should return user's keys, not error)
curl -s -X GET http://localhost:8001/api/v1/keys/ \
  -H "Cookie: access_token=<JWT_from_above>"
```

**Expected:** 200 OK with key list

---

## Error Cases

### Backend Unavailable

Stop backend and try login:
```bash
curl -s -X POST http://localhost:8001/api/v1/auth/telegram-callback \
  -H "Content-Type: application/json" \
  -d '{...}' 
```

**Expected:** 503 Service Unavailable

### Invalid CAPTCHA

```bash
curl -s -X POST http://localhost:8001/api/v1/auth/telegram-callback \
  -H "Content-Type: application/json" \
  -d '{
    ...
    "captcha_answer": 999
  }'
```

**Expected:** 400 Bad Request

---

## Logs to Monitor

**Backend logs:**
- Look for: `GET /users/{tg_id}` (404 or 200)
- Look for: `POST /users` (201 created)

**Web logs:**
- Look for: `Checking if user exists: tg_id=...`
- Look for: `✓ Existing user login` or `✓ New user created`
- Look for: `✓ Login successful`

---

## Browser Testing

1. Open http://localhost:8001/ in browser
2. Click "Login with Telegram"
3. In Telegram, go to bot and complete auth flow
4. Browser should redirect to dashboard after successful login
