# Telegram Bot Migration Summary

## Overview

Successfully migrated **core business logic** from the Telegram bot into the FastAPI backend. The bot now calls the backend HTTP API instead of accessing the database directly.

## What Was Implemented

### 1. User Management
- **`POST /api/v1/bot/users`** - Register/upsert user on first bot `/start`
  - Accepts: `tg_id`, `username`, `first_name`, `last_name`, `language_code`, `referral_token` (optional)
  - Returns: User object with trial status and balance

- **`GET /api/v1/bot/users/{tg_id}`** - Get user info
  - Returns: User data for UI rendering

### 2. Pricing & Discounts
- **`GET /api/v1/bot/users/{tg_id}/price`** - Calculate price with discounts
  - Query params: `tariff_id`, `months`
  - Applies:
    - Personal discount (from `stocks` table) - fix or percent
    - Volume discount (3%) for 2-6 month subscriptions
    - Referral discount (from `users.balance`)
  - Returns: `PriceResult` with breakdown

### 3. Trial Keys
- **`POST /api/v1/bot/keys/trial`** - Create free trial key
  - Checks: `user.trial == 0` (not yet used)
  - Creates key using trial tariff (default: tariff_id=10)
  - Sets `user.trial = 1` (marks as used)
  - Returns: Key data (VLESS link, email, expiry)

### 4. Payments
- **`POST /api/v1/bot/payments`** - Create payment for new key or renewal
  - New key: `tg_id`, `tariff_id`, `months`
  - Renewal: `tg_id`, `email` (of existing key), `months`
  - Calculates price → creates YooKassa payment
  - Stores in DB: `payment_type` = `"create_key|{tariff_id}"` or `"renew_key|{email}"`
  - Returns: `payment_id`, `payment_url`, final amount with discount breakdown

### 5. Referral System
- **`GET /api/v1/bot/referral/{tg_id}/link`** - Get or create referral link
  - Returns: Shareable URL with token
  - Example: `https://t.me/bot_username?start=abc123def456`

- **`GET /api/v1/bot/referral/{tg_id}/stats`** - Get referral statistics
  - Returns: Number of referred users, total rewards earned, share URL

- **Auto-processing**:
  - When user registers via referral token → `process_redemption()` sets `user.referral_id`
  - When user makes first payment → webhook calls `process_referral_bonus()`:
    - Awards 10% of payment to referrer
    - Adds to referrer's `balance` (usable for future payments)
    - Creates `referral_reward` record
    - Sets `user.check_referral = true` (one-time only)

### 6. Payment Webhook Enhancement
- Extended `POST /api/v1/payments/webhook` to handle:
  - Bot payment format: `"create_key|{tariff_id}"` and `"renew_key|{email}"`
  - Web payment format: `"web_new_key|{tg_id}:{tariff_id}"` and `"web_renew_key|{client_id}:{tariff_id}"`
  - After key creation/renewal:
    - Process referral bonus (if applicable)
    - Deduct referral discount from `user.balance`

## Database Changes

### New Tables
1. **`stocks`** - Per-user discounts (replaces legacy global promo codes)
   - Columns: `tg_id` (PK), `stock_type` (fix/percent), `value`, `is_active`, `valid_until`

2. **`referral_links`** - Referral tracking
   - Columns: `id` (PK), `referrer_tg_id`, `token` (unique), `created_at`

3. **`referral_redemptions`** - When user registers via referral
   - Columns: `id`, `referral_link_id`, `referred_tg_id`, `redeemed_at`

4. **`referral_rewards`** - Bonus records
   - Columns: `id`, `referrer_tg_id`, `reward_type`, `reward_value`, `awarded_at`, `is_claimed`

### Modified Tables
1. **`payments`** - Added column:
   - `referral_discount REAL DEFAULT 0.0` - Amount deducted from user balance at payment time

## Configuration (`.env`)

New settings required:
```env
DEFAULT_TRIAL_TARIFF_ID=10              # Tariff ID for free trial (amount must be 0)
DEFAULT_SERVER_ID=2                     # Server ID for new users (hardcoded in bot)
REFERRAL_BONUS_PERCENT=0.10             # 10% of payment to referrer
VOLUME_DISCOUNT_PERCENT=0.03            # 3% discount for 2-6 month subscriptions
```

## Bot Integration (Next Steps)

The bot should now:

1. **On `/start`**: 
   ```
   POST /api/v1/bot/users {tg_id, username, first_name, referral_token?}
   ```

2. **For trial activation**:
   ```
   POST /api/v1/bot/keys/trial {tg_id}
   ```

3. **For payment creation**:
   ```
   POST /api/v1/bot/payments {tg_id, tariff_id, months, email?}
   ```

4. **For payment status polling** (existing):
   ```
   GET /api/v1/payments/{payment_id}/status
   ```

5. **To get user balance/trial status**:
   ```
   GET /api/v1/bot/users/{tg_id}
   ```

6. **For referral sharing**:
   ```
   GET /api/v1/bot/referral/{tg_id}/link
   ```

## What the Bot Still Does

- **Telegram UI**: Dialog flows, buttons, inline keyboards
- **Message sending**: Sends key links, notifications, confirmations
- **Notification scheduling**: Reads `notified_24h/10h` flags from DB, sends expiry reminders
- **Telegram updates**: Receives and processes `/start`, callback queries, messages

## What Was NOT Migrated (Out of Scope)

- Gift links system (not in Phase 1 scope)
- Analytics & metrics (separate from core payment flow)
- Background sync tasks (XUI ↔ DB sync, notification scheduling)
- Admin mass operations (not needed for bot flow)

## Testing

All existing tests pass:
```bash
pytest tests/ -v
# 41 tests, all passing ✓
```

To test bot endpoints manually:
```bash
curl -X POST http://localhost:8000/api/v1/bot/users \
  -H "X-Bot-Secret: $BOT_SECRET_KEY" \
  -H "Content-Type: application/json" \
  -d '{"tg_id": 123, "username": "test_user", "first_name": "Test"}'
```

## Migrations

Apply in order:
```bash
psql "$DATABASE_URL" -f migrations/003_stocks_per_user.sql
psql "$DATABASE_URL" -f migrations/004_referral_tables.sql
psql "$DATABASE_URL" -f migrations/005_add_referral_discount.sql
```

Or use your migration tool (Alembic, etc.) if configured.
