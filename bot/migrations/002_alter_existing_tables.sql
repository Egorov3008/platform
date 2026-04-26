-- ============================================================================
-- Миграция 002: Изменение существующих таблиц
-- ============================================================================
-- Описание: Добавляет отсутствующие поля в существующие таблицы
-- Приоритет: Критично для работы с ключами и пользователями
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 1. Таблица users: добавляем balance и is_blocked
-- ----------------------------------------------------------------------------
-- Поле balance может уже существовать в некоторых версиях БД
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'users' AND column_name = 'balance') THEN
        ALTER TABLE users ADD COLUMN balance REAL NOT NULL DEFAULT 0.0;
        RAISE NOTICE 'Добавлено поле users.balance';
    ELSE
        RAISE NOTICE 'Поле users.balance уже существует';
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'users' AND column_name = 'is_blocked') THEN
        ALTER TABLE users ADD COLUMN is_blocked BOOLEAN NOT NULL DEFAULT FALSE;
        RAISE NOTICE 'Добавлено поле users.is_blocked';
    ELSE
        RAISE NOTICE 'Поле users.is_blocked уже существует';
    END IF;
END $$;

COMMENT ON COLUMN users.balance IS 'Баланс пользователя в рублях';
COMMENT ON COLUMN users.is_blocked IS 'Флаг блокировки пользователя';

-- ----------------------------------------------------------------------------
-- 2. Таблица keys: добавляем поля тарифа и статистики
-- ----------------------------------------------------------------------------
-- tariff_description
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'keys' AND column_name = 'tariff_description') THEN
        ALTER TABLE keys ADD COLUMN tariff_description TEXT;
        RAISE NOTICE 'Добавлено поле keys.tariff_description';
    ELSE
        RAISE NOTICE 'Поле keys.tariff_description уже существует';
    END IF;
END $$;

-- name_tariff
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'keys' AND column_name = 'name_tariff') THEN
        ALTER TABLE keys ADD COLUMN name_tariff TEXT;
        RAISE NOTICE 'Добавлено поле keys.name_tariff';
    ELSE
        RAISE NOTICE 'Поле keys.name_tariff уже существует';
    END IF;
END $$;

-- amount
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'keys' AND column_name = 'amount') THEN
        ALTER TABLE keys ADD COLUMN amount REAL;
        RAISE NOTICE 'Добавлено поле keys.amount';
    ELSE
        RAISE NOTICE 'Поле keys.amount уже существует';
    END IF;
END $$;

-- limit_ip
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'keys' AND column_name = 'limit_ip') THEN
        ALTER TABLE keys ADD COLUMN limit_ip INTEGER;
        RAISE NOTICE 'Добавлено поле keys.limit_ip';
    ELSE
        RAISE NOTICE 'Поле keys.limit_ip уже существует';
    END IF;
END $$;

-- period
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'keys' AND column_name = 'period') THEN
        ALTER TABLE keys ADD COLUMN period INTEGER;
        RAISE NOTICE 'Добавлено поле keys.period';
    ELSE
        RAISE NOTICE 'Поле keys.period уже существует';
    END IF;
END $$;

-- used_traffic
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'keys' AND column_name = 'used_traffic') THEN
        ALTER TABLE keys ADD COLUMN used_traffic REAL NOT NULL DEFAULT 0.0;
        RAISE NOTICE 'Добавлено поле keys.used_traffic';
    ELSE
        RAISE NOTICE 'Поле keys.used_traffic уже существует';
    END IF;
END $$;

-- server_info (JSONB для хранения данных сервера)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'keys' AND column_name = 'server_info') THEN
        ALTER TABLE keys ADD COLUMN server_info JSONB;
        RAISE NOTICE 'Добавлено поле keys.server_info';
    ELSE
        RAISE NOTICE 'Поле keys.server_info уже существует';
    END IF;
END $$;

COMMENT ON COLUMN keys.tariff_description IS 'Описание тарифа ключа';
COMMENT ON COLUMN keys.name_tariff IS 'Название тарифа ключа';
COMMENT ON COLUMN keys.amount IS 'Стоимость тарифа';
COMMENT ON COLUMN keys.limit_ip IS 'Лимит IP подключений';
COMMENT ON COLUMN keys.period IS 'Период тарифа в днях';
COMMENT ON COLUMN keys.used_traffic IS 'Использованный трафик в GB';
COMMENT ON COLUMN keys.server_info IS 'Данные сервера (JSONB)';

-- ----------------------------------------------------------------------------
-- 3. Таблица gift_links: добавляем поля получателя
-- ----------------------------------------------------------------------------
-- recipient_tg_id
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'gift_links' AND column_name = 'recipient_tg_id') THEN
        ALTER TABLE gift_links ADD COLUMN recipient_tg_id BIGINT;
        RAISE NOTICE 'Добавлено поле gift_links.recipient_tg_id';
    ELSE
        RAISE NOTICE 'Поле gift_links.recipient_tg_id уже существует';
    END IF;
END $$;

-- email
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'gift_links' AND column_name = 'email') THEN
        ALTER TABLE gift_links ADD COLUMN email TEXT;
        RAISE NOTICE 'Добавлено поле gift_links.email';
    ELSE
        RAISE NOTICE 'Поле gift_links.email уже существует';
    END IF;
END $$;

-- used_at
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'gift_links' AND column_name = 'used_at') THEN
        ALTER TABLE gift_links ADD COLUMN used_at TIMESTAMP WITH TIME ZONE;
        RAISE NOTICE 'Добавлено поле gift_links.used_at';
    ELSE
        RAISE NOTICE 'Поле gift_links.used_at уже существует';
    END IF;
END $$;

COMMENT ON COLUMN gift_links.recipient_tg_id IS 'TG ID получателя подарка';
COMMENT ON COLUMN gift_links.email IS 'Email для активации подарка';
COMMENT ON COLUMN gift_links.used_at IS 'Дата активации подарка';

-- Добавляем FK для recipient_tg_id (если поле добавлено)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint
                   WHERE conname = 'fk_gift_links_recipient') THEN
        ALTER TABLE gift_links
        ADD CONSTRAINT fk_gift_links_recipient
        FOREIGN KEY (recipient_tg_id) REFERENCES users(tg_id) ON DELETE SET NULL;
        RAISE NOTICE 'Добавлен FK gift_links.recipient_tg_id -> users.tg_id';
    ELSE
        RAISE NOTICE 'FK gift_links.recipient_tg_id уже существует';
    END IF;
END $$;

-- ----------------------------------------------------------------------------
-- Логирование применения миграции
-- ----------------------------------------------------------------------------
DO $$
BEGIN
    RAISE NOTICE 'Миграция 002: Изменены таблицы - users, keys, gift_links';
END $$;

COMMIT;
