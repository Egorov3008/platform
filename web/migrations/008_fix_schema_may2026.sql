-- Migration 008: Fix critical schema mismatches (May 2026)
--
-- Issues fixed:
-- 1. stocks table still in legacy global-promo format → per-user discount format
-- 2. users.referral_id missing (exists in User model, not in DB)
-- 3. payments.referral_discount nullable or missing (PaymentModel expects it)
-- 4. keys.email missing UNIQUE constraint (backend uses email as sole identifier)
-- 5. Invalid keys.inbound_id FK referencing inbound(inbound_id) (not globally unique)
-- 6. keys.total_gb default 0.0 vs Key model default 10
-- 7. gift_links table missing (DataService queries it, schema.sql only had gifts)

BEGIN;

-- 1. Migrate stocks to per-user format if still in old global-promo format.
--    The legacy table is incompatible with the Stock dataclass, so data is not migrated.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'stocks' AND column_name = 'discount_type'
    ) THEN
        DROP TABLE stocks;
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS stocks (
    tg_id       BIGINT PRIMARY KEY REFERENCES users(tg_id) ON DELETE CASCADE,
    stock_type  TEXT NOT NULL CHECK (stock_type IN ('fix', 'percent')),
    value       DECIMAL(10,2) NOT NULL,
    is_active   BOOLEAN NOT NULL DEFAULT true,
    valid_until TIMESTAMPTZ,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_stocks_active ON stocks(is_active, valid_until);

-- 2. Add referral_id to users (User model expects Optional[int])
ALTER TABLE users ADD COLUMN IF NOT EXISTS referral_id INTEGER;

-- 3. Ensure referral_discount is present and NOT NULL.
--    Migration 005 added it as nullable with DEFAULT. We backfill and enforce NOT NULL.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'payments' AND column_name = 'referral_discount'
    ) THEN
        UPDATE payments SET referral_discount = 0.0 WHERE referral_discount IS NULL;
        ALTER TABLE payments ALTER COLUMN referral_discount SET NOT NULL;
    ELSE
        ALTER TABLE payments ADD COLUMN referral_discount REAL NOT NULL DEFAULT 0.0;
    END IF;
END $$;

-- 4. UNIQUE constraint on keys.email (backend uses email as the single identifier)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'uq_keys_email' AND conrelid = 'keys'::regclass
    ) THEN
        ALTER TABLE keys ADD CONSTRAINT uq_keys_email UNIQUE (email);
    END IF;
END $$;

-- 5. Drop any invalid foreign key on keys.inbound_id.
--    schema.sql referenced inbound(inbound_id) which is not a unique column globally.
DO $$
DECLARE
    fk_name text;
BEGIN
    SELECT tc.constraint_name INTO fk_name
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu
      ON tc.constraint_name = kcu.constraint_name
    WHERE tc.table_name = 'keys'
      AND tc.constraint_type = 'FOREIGN KEY'
      AND kcu.column_name = 'inbound_id';

    IF fk_name IS NOT NULL THEN
        EXECUTE format('ALTER TABLE keys DROP CONSTRAINT %I', fk_name);
    END IF;
END $$;

-- 6. Align keys.total_gb default with Key dataclass default (10 instead of 0)
ALTER TABLE keys ALTER COLUMN total_gb SET DEFAULT 10.0;

-- 7. gift_links table (DataService uses gift_links; old schema.sql had gifts instead)
CREATE TABLE IF NOT EXISTS gift_links (
    id              SERIAL PRIMARY KEY,
    sender_tg_id    INTEGER NOT NULL,
    tariff_id       INTEGER NOT NULL,
    token           TEXT NOT NULL,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    recipient_tg_id BIGINT,
    email           TEXT,
    used_at         TIMESTAMP WITH TIME ZONE,
    CONSTRAINT fk_gift_sender FOREIGN KEY (sender_tg_id) REFERENCES users (tg_id),
    CONSTRAINT fk_gift_recipient FOREIGN KEY (recipient_tg_id) REFERENCES users (tg_id)
);

COMMIT;
