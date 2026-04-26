-- ============================================================================
-- Откат миграции 001: Удаление созданных таблиц
-- ============================================================================
-- Описание: Удаляет таблицы, созданные миграцией 001
-- Внимание: Все данные в этих таблицах будут потеряны
-- Предупреждение: Таблицы могут иметь зависимости (FK)
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 1. Удаление таблиц в порядке, обратном созданию
--    (сначала таблицы с FK, потом на которые ссылаются)
-- ----------------------------------------------------------------------------

-- referral_rewards (ссылается на users)
DROP TABLE IF EXISTS referral_rewards CASCADE;
DO $$
BEGIN
    RAISE NOTICE 'Удалена таблица referral_rewards';
END $$;

-- referral_redemptions (ссылается на referral_links, users)
DROP TABLE IF EXISTS referral_redemptions CASCADE;
DO $$
BEGIN
    RAISE NOTICE 'Удалена таблица referral_redemptions';
END $$;

-- referral_links (ссылается на users)
DROP TABLE IF EXISTS referral_links CASCADE;
DO $$
BEGIN
    RAISE NOTICE 'Удалена таблица referral_links';
END $$;

-- mass_mailing (не имеет FK)
DROP TABLE IF EXISTS mass_mailing CASCADE;
DO $$
BEGIN
    RAISE NOTICE 'Удалена таблица mass_mailing';
END $$;

-- cache (не имеет FK)
DROP TABLE IF EXISTS cache CASCADE;
DO $$
BEGIN
    RAISE NOTICE 'Удалена таблица cache';
END $$;

-- ----------------------------------------------------------------------------
-- Логирование
-- ----------------------------------------------------------------------------
DO $$
BEGIN
    RAISE NOTICE 'Откат миграции 001: Удалены все созданные таблицы';
    RAISE WARNING 'Данные в таблицах безвозвратно потеряны';
END $$;

COMMIT;
