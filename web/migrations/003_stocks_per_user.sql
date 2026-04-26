-- Per-user discount/stock system
-- Replaces the legacy global promo codes table with per-user records
CREATE TABLE IF NOT EXISTS stocks (
    tg_id       BIGINT PRIMARY KEY REFERENCES users(tg_id) ON DELETE CASCADE,
    stock_type  TEXT NOT NULL CHECK (stock_type IN ('fix', 'percent')),
    value       DECIMAL(10,2) NOT NULL,
    is_active   BOOLEAN NOT NULL DEFAULT true,
    valid_until TIMESTAMPTZ,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_stocks_active ON stocks(is_active, valid_until);
