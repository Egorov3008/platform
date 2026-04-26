-- Миграция: Реферальная система
-- Добавляет таблицы для реферальных ссылок, использований и наград

-- Добавить поля referral_id и check_referral в users (если ещё нет)
ALTER TABLE users ADD COLUMN IF NOT EXISTS referral_id BIGINT NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS check_referral BOOLEAN DEFAULT FALSE;

-- Таблица реферальных ссылок
CREATE TABLE IF NOT EXISTS referral_links (
    id              SERIAL PRIMARY KEY,
    referrer_tg_id  BIGINT NOT NULL REFERENCES users(tg_id) ON DELETE CASCADE,
    token           TEXT NOT NULL UNIQUE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Таблица использований реферальных ссылок
CREATE TABLE IF NOT EXISTS referral_redemptions (
    id                SERIAL PRIMARY KEY,
    referral_link_id  INTEGER NOT NULL REFERENCES referral_links(id) ON DELETE CASCADE,
    referred_tg_id    BIGINT NOT NULL REFERENCES users(tg_id) ON DELETE CASCADE,
    redeemed_at       TIMESTAMPTZ DEFAULT NOW()
);

-- Таблица наград за рефералов
CREATE TABLE IF NOT EXISTS referral_rewards (
    id              SERIAL PRIMARY KEY,
    referrer_tg_id  BIGINT NOT NULL REFERENCES users(tg_id) ON DELETE CASCADE,
    reward_type     TEXT NOT NULL,           -- 'discount_percent'
    reward_value    TEXT NOT NULL,           -- Значение награды (напр. '0.10')
    awarded_at      TIMESTAMPTZ DEFAULT NOW(),
    is_claimed      BOOLEAN DEFAULT FALSE
);

-- Индексы
CREATE INDEX IF NOT EXISTS idx_referral_links_token ON referral_links(token);
CREATE INDEX IF NOT EXISTS idx_referral_links_referrer ON referral_links(referrer_tg_id);
CREATE INDEX IF NOT EXISTS idx_referral_redemptions_link ON referral_redemptions(referral_link_id);
CREATE INDEX IF NOT EXISTS idx_referral_redemptions_referred ON referral_redemptions(referred_tg_id);
CREATE INDEX IF NOT EXISTS idx_referral_rewards_referrer ON referral_rewards(referrer_tg_id);
CREATE INDEX IF NOT EXISTS idx_referral_rewards_unclaimed ON referral_rewards(is_claimed) WHERE is_claimed = FALSE;
