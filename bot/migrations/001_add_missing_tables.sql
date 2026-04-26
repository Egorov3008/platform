-- ============================================================================
-- Миграция 001: Создание отсутствующих таблиц
-- ============================================================================
-- Описание: Создает таблицы, которые есть в schema.sql, но отсутствуют в БД
-- Приоритет: Критично для работы кеша и реферальной программы
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 1. Таблица cache (для кеширования данных)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cache (
    key TEXT NOT NULL PRIMARY KEY,
    value JSONB NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE
);

COMMENT ON TABLE cache IS 'Кеш для хранения временных данных приложения';
COMMENT ON COLUMN cache.key IS 'Уникальный ключ кеша';
COMMENT ON COLUMN cache.value IS 'Значение в формате JSONB';
COMMENT ON COLUMN cache.expires_at IS 'Время истечения срока действия (NULL = бессрочно)';

CREATE INDEX IF NOT EXISTS idx_cache_expires_at ON cache(expires_at) WHERE expires_at IS NOT NULL;

-- ----------------------------------------------------------------------------
-- 2. Таблица mass_mailing (для массовых рассылок)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS mass_mailing (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    emoji TEXT NOT NULL
);

COMMENT ON TABLE mass_mailing IS 'Шаблоны массовых рассылок';
COMMENT ON COLUMN mass_mailing.title IS 'Заголовок рассылки';
COMMENT ON COLUMN mass_mailing.emoji IS 'Emoji для рассылки';

-- ----------------------------------------------------------------------------
-- 3. Таблица referral_links (для реферальных ссылок)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS referral_links (
    id SERIAL PRIMARY KEY,
    referrer_tg_id BIGINT NOT NULL REFERENCES users(tg_id) ON DELETE CASCADE,
    token TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE referral_links IS 'Реферальные ссылки пользователей';
COMMENT ON COLUMN referral_links.referrer_tg_id IS 'TG ID пользователя, создавшего ссылку';
COMMENT ON COLUMN referral_links.token IS 'Уникальный токен ссылки';
COMMENT ON COLUMN referral_links.created_at IS 'Дата создания ссылки';

CREATE INDEX IF NOT EXISTS idx_referral_links_token ON referral_links(token);
CREATE INDEX IF NOT EXISTS idx_referral_links_referrer ON referral_links(referrer_tg_id);

-- ----------------------------------------------------------------------------
-- 4. Таблица referral_redemptions (для активаций реферальных ссылок)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS referral_redemptions (
    id SERIAL PRIMARY KEY,
    referral_link_id INTEGER NOT NULL REFERENCES referral_links(id) ON DELETE CASCADE,
    referred_tg_id BIGINT NOT NULL REFERENCES users(tg_id) ON DELETE CASCADE,
    redeemed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (referral_link_id, referred_tg_id)
);

COMMENT ON TABLE referral_redemptions IS 'Активации реферальных ссылок';
COMMENT ON COLUMN referral_redemptions.referral_link_id IS 'ID реферальной ссылки';
COMMENT ON COLUMN referral_redemptions.referred_tg_id IS 'TG ID пользователя, активировавшего ссылку';
COMMENT ON COLUMN referral_redemptions.redeemed_at IS 'Дата активации';

CREATE INDEX IF NOT EXISTS idx_referral_redemptions_link ON referral_redemptions(referral_link_id);
CREATE INDEX IF NOT EXISTS idx_referral_redemptions_referred ON referral_redemptions(referred_tg_id);

-- ----------------------------------------------------------------------------
-- 5. Таблица referral_rewards (для наград реферальной программы)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS referral_rewards (
    id SERIAL PRIMARY KEY,
    referrer_tg_id BIGINT NOT NULL REFERENCES users(tg_id) ON DELETE CASCADE,
    reward_type TEXT NOT NULL,
    reward_value TEXT NOT NULL,
    awarded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_claimed BOOLEAN DEFAULT FALSE
);

COMMENT ON TABLE referral_rewards IS 'Награды реферальной программы';
COMMENT ON COLUMN referral_rewards.referrer_tg_id IS 'TG ID пользователя, получившего награду';
COMMENT ON COLUMN referral_rewards.reward_type IS 'Тип награды (bonus, discount, etc.)';
COMMENT ON COLUMN referral_rewards.reward_value IS 'Значение награды';
COMMENT ON COLUMN referral_rewards.awarded_at IS 'Дата начисления награды';
COMMENT ON COLUMN referral_rewards.is_claimed IS 'Флаг получения награды';

CREATE INDEX IF NOT EXISTS idx_referral_rewards_referrer ON referral_rewards(referrer_tg_id);
CREATE INDEX IF NOT EXISTS idx_referral_rewards_claimed ON referral_rewards(is_claimed) WHERE is_claimed = FALSE;

-- ----------------------------------------------------------------------------
-- Логирование применения миграции
-- ----------------------------------------------------------------------------
DO $$
BEGIN
    RAISE NOTICE 'Миграция 001: Созданы таблицы - cache, mass_mailing, referral_links, referral_redemptions, referral_rewards';
END $$;

COMMIT;
