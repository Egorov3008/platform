-- ============================================================================
-- Миграция 004: Индексы и ограничения
-- ============================================================================
-- Описание: Создает индексы для оптимизации запросов и дополнительные FK
-- Приоритет: Средний (улучшает производительность)
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 1. Индексы для таблицы keys
-- ----------------------------------------------------------------------------

-- Индекс для поиска по тарифу
CREATE INDEX IF NOT EXISTS idx_keys_tariff_id ON keys(tariff_id) WHERE tariff_id IS NOT NULL;

-- Индекс для поиска по inbound
CREATE INDEX IF NOT EXISTS idx_keys_inbound_id ON keys(inbound_id) WHERE inbound_id IS NOT NULL;

-- Индекс для мониторинга использованного трафика
CREATE INDEX IF NOT EXISTS idx_keys_used_traffic ON keys(used_traffic);

-- Составной индекс для сегментации ключей (истекающие, активные)
CREATE INDEX IF NOT EXISTS idx_keys_expiry_active ON keys(expiry_time);

DO $$
BEGIN
    RAISE NOTICE 'Созданы индексы для таблицы keys';
END $$;

-- ----------------------------------------------------------------------------
-- 2. Индексы для таблицы users
-- ----------------------------------------------------------------------------

-- Индекс для поиска заблокированных пользователей
CREATE INDEX IF NOT EXISTS idx_users_is_blocked ON users(is_blocked) WHERE is_blocked = TRUE;

-- Индекс для поиска по балансу (для уведомлений о пополнении)
CREATE INDEX IF NOT EXISTS idx_users_balance ON users(balance) WHERE balance > 0;

DO $$
BEGIN
    RAISE NOTICE 'Созданы индексы для таблицы users';
END $$;

-- ----------------------------------------------------------------------------
-- 3. Индексы для таблицы gift_links
-- ----------------------------------------------------------------------------

-- Индекс для поиска активных подарков (не использованных)
CREATE INDEX IF NOT EXISTS idx_gift_links_active ON gift_links(recipient_tg_id) 
WHERE recipient_tg_id IS NULL;

-- Индекс для поиска по sender
CREATE INDEX IF NOT EXISTS idx_gift_links_sender ON gift_links(sender_tg_id);

DO $$
BEGIN
    RAISE NOTICE 'Созданы индексы для таблицы gift_links';
END $$;

-- ----------------------------------------------------------------------------
-- 4. Индексы для таблицы gifts (старая структура)
-- ----------------------------------------------------------------------------

-- Индекс для поиска использованных подарков
CREATE INDEX IF NOT EXISTS idx_gifts_is_used ON gifts(is_used) WHERE is_used = TRUE;

-- Индекс для поиска по отправителю
CREATE INDEX IF NOT EXISTS idx_gifts_sender ON gifts(sender_tg_id);

-- Индекс для поиска по получателю
CREATE INDEX IF NOT EXISTS idx_gifts_recipient ON gifts(recipient_tg_id) WHERE recipient_tg_id IS NOT NULL;

DO $$
BEGIN
    RAISE NOTICE 'Созданы индексы для таблицы gifts';
END $$;

-- ----------------------------------------------------------------------------
-- 5. Проверка целостности FOREIGN KEY
-- ----------------------------------------------------------------------------

DO $$
DECLARE
    orphan_gifts INTEGER;
BEGIN
    SELECT COUNT(*) INTO orphan_gifts
    FROM gift_links g
    LEFT JOIN users u ON g.sender_tg_id = u.tg_id
    WHERE u.tg_id IS NULL;
    
    IF orphan_gifts > 0 THEN
        RAISE WARNING 'Найдено сиротских записей gift_links (без sender): %', orphan_gifts;
    ELSE
        RAISE NOTICE 'Все записи gift_links имеют корректные ссылки на users';
    END IF;
END $$;

-- ----------------------------------------------------------------------------
-- 6. Обновление статистики анализатора
-- ----------------------------------------------------------------------------
ANALYZE users;
ANALYZE keys;
ANALYZE tariff;
ANALYZE gifts;
ANALYZE gift_links;
ANALYZE gift_redemptions;
ANALYZE referrals;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'referral_links') THEN
        ANALYZE referral_links;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'referral_redemptions') THEN
        ANALYZE referral_redemptions;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'referral_rewards') THEN
        ANALYZE referral_rewards;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'cache') THEN
        ANALYZE cache;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'mass_mailing') THEN
        ANALYZE mass_mailing;
    END IF;
    RAISE NOTICE 'Обновлена статистика анализатора для всех таблиц';
END $$;

-- ----------------------------------------------------------------------------
-- Логирование применения миграции
-- ----------------------------------------------------------------------------
DO $$
BEGIN
    RAISE NOTICE 'Миграция 004: Созданы индексы и проверены FK';
END $$;

COMMIT;
