-- Referral system tables
-- Only create if they don't already exist (may be present from bot DB)

CREATE TABLE IF NOT EXISTS referral_links (
    id              SERIAL PRIMARY KEY,
    referrer_tg_id  BIGINT NOT NULL REFERENCES users(tg_id) ON DELETE CASCADE,
    token           VARCHAR(255) UNIQUE NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS referral_redemptions (
    id               SERIAL PRIMARY KEY,
    referral_link_id INTEGER NOT NULL REFERENCES referral_links(id) ON DELETE CASCADE,
    referred_tg_id   BIGINT NOT NULL REFERENCES users(tg_id) ON DELETE CASCADE,
    redeemed_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(referral_link_id, referred_tg_id)
);

CREATE TABLE IF NOT EXISTS referral_rewards (
    id              SERIAL PRIMARY KEY,
    referrer_tg_id  BIGINT NOT NULL REFERENCES users(tg_id) ON DELETE CASCADE,
    reward_type     TEXT DEFAULT 'referral_bonus',
    reward_value    DECIMAL(10,2) NOT NULL,
    awarded_at      TIMESTAMPTZ DEFAULT NOW(),
    is_claimed      BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_referral_links_referrer ON referral_links(referrer_tg_id);
CREATE INDEX IF NOT EXISTS idx_referral_links_token ON referral_links(token);
CREATE INDEX IF NOT EXISTS idx_referral_redemptions_referred ON referral_redemptions(referred_tg_id);
CREATE INDEX IF NOT EXISTS idx_referral_rewards_referrer ON referral_rewards(referrer_tg_id);
