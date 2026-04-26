-- ============================================================================
-- Откат миграции 002: Откат изменений существующих таблиц
-- ============================================================================
-- Описание: Удаляет поля, добавленные миграцией 002
-- Внимание: Данные в удаляемых полях будут потеряны
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 1. Таблица users: удаляем добавленные поля
-- ----------------------------------------------------------------------------

-- is_blocked
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'users' AND column_name = 'is_blocked') THEN
        ALTER TABLE users DROP COLUMN is_blocked;
        RAISE NOTICE 'Удалено поле users.is_blocked';
    ELSE
        RAISE NOTICE 'Поле users.is_blocked не существует';
    END IF;
END $$;

-- balance (осторожно! может использоваться в приложении)
-- Закомментировано по умолчанию
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'users' AND column_name = 'balance') THEN
        -- ALTER TABLE users DROP COLUMN balance;
        RAISE NOTICE 'Поле users.balance сохранено (закомментировано DROP)';
    ELSE
        RAISE NOTICE 'Поле users.balance не существует';
    END IF;
END $$;

-- ----------------------------------------------------------------------------
-- 2. Таблица keys: удаляем добавленные поля
-- ----------------------------------------------------------------------------

-- tariff_description
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'keys' AND column_name = 'tariff_description') THEN
        -- ALTER TABLE keys DROP COLUMN tariff_description;
        RAISE NOTICE 'Поле keys.tariff_description сохранено (закомментировано DROP)';
    ELSE
        RAISE NOTICE 'Поле keys.tariff_description не существует';
    END IF;
END $$;

-- name_tariff
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'keys' AND column_name = 'name_tariff') THEN
        -- ALTER TABLE keys DROP COLUMN name_tariff;
        RAISE NOTICE 'Поле keys.name_tariff сохранено (закомментировано DROP)';
    ELSE
        RAISE NOTICE 'Поле keys.name_tariff не существует';
    END IF;
END $$;

-- amount
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'keys' AND column_name = 'amount') THEN
        -- ALTER TABLE keys DROP COLUMN amount;
        RAISE NOTICE 'Поле keys.amount сохранено (закомментировано DROP)';
    ELSE
        RAISE NOTICE 'Поле keys.amount не существует';
    END IF;
END $$;

-- limit_ip
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'keys' AND column_name = 'limit_ip') THEN
        -- ALTER TABLE keys DROP COLUMN limit_ip;
        RAISE NOTICE 'Поле keys.limit_ip сохранено (закомментировано DROP)';
    ELSE
        RAISE NOTICE 'Поле keys.limit_ip не существует';
    END IF;
END $$;

-- period
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'keys' AND column_name = 'period') THEN
        -- ALTER TABLE keys DROP COLUMN period;
        RAISE NOTICE 'Поле keys.period сохранено (закомментировано DROP)';
    ELSE
        RAISE NOTICE 'Поле keys.period не существует';
    END IF;
END $$;

-- used_traffic
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'keys' AND column_name = 'used_traffic') THEN
        -- ALTER TABLE keys DROP COLUMN used_traffic;
        RAISE NOTICE 'Поле keys.used_traffic сохранено (закомментировано DROP)';
    ELSE
        RAISE NOTICE 'Поле keys.used_traffic не существует';
    END IF;
END $$;

-- server_info
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'keys' AND column_name = 'server_info') THEN
        -- ALTER TABLE keys DROP COLUMN server_info;
        RAISE NOTICE 'Поле keys.server_info сохранено (закомментировано DROP)';
    ELSE
        RAISE NOTICE 'Поле keys.server_info не существует';
    END IF;
END $$;

-- ----------------------------------------------------------------------------
-- 3. Таблица gift_links: удаляем добавленные поля
-- ----------------------------------------------------------------------------

-- recipient_tg_id (сначала нужно удалить FK)
ALTER TABLE gift_links DROP CONSTRAINT IF EXISTS fk_gift_links_recipient;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'gift_links' AND column_name = 'recipient_tg_id') THEN
        -- ALTER TABLE gift_links DROP COLUMN recipient_tg_id;
        RAISE NOTICE 'Поле gift_links.recipient_tg_id сохранено (закомментировано DROP)';
    ELSE
        RAISE NOTICE 'Поле gift_links.recipient_tg_id не существует';
    END IF;
END $$;

-- email
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'gift_links' AND column_name = 'email') THEN
        -- ALTER TABLE gift_links DROP COLUMN email;
        RAISE NOTICE 'Поле gift_links.email сохранено (закомментировано DROP)';
    ELSE
        RAISE NOTICE 'Поле gift_links.email не существует';
    END IF;
END $$;

-- used_at
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'gift_links' AND column_name = 'used_at') THEN
        -- ALTER TABLE gift_links DROP COLUMN used_at;
        RAISE NOTICE 'Поле gift_links.used_at сохранено (закомментировано DROP)';
    ELSE
        RAISE NOTICE 'Поле gift_links.used_at не существует';
    END IF;
END $$;

-- ----------------------------------------------------------------------------
-- Логирование
-- ----------------------------------------------------------------------------
DO $$
BEGIN
    RAISE NOTICE 'Откат миграции 002: Поля сохранены (закомментировано DROP)';
    RAISE NOTICE 'Для полного удаления раскомментируйте DROP команды';
END $$;

COMMIT;
