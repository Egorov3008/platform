-- ============================================================================
-- Миграция 007: Исправление типов параметров для bigint полей
-- ============================================================================
-- Проблема: asyncpg не может автоматически определить тип для значений > 2^31-1
-- Ошибка: "invalid input for query argument $N: XXXX (value out of int32 range)"
-- Решение: Явное приведение типов в запросах через CAST или ::bigint
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- Примечание: Эта миграция не изменяет схему БД (все поля уже bigint).
-- Вместо этого требуется исправление в backend/database/base.py:
-- - Метод create() должен использовать ::bigint для полей типа bigint
-- - Или использовать именованные параметры с явным указанием типа
-- ----------------------------------------------------------------------------

-- Проверка текущих типов полей
DO $$
DECLARE
    col_type TEXT;
BEGIN
    -- Проверка users.tg_id
    SELECT data_type INTO col_type FROM information_schema.columns
    WHERE table_name = 'users' AND column_name = 'tg_id';
    IF col_type != 'bigint' THEN
        RAISE EXCEPTION 'users.tg_id должен быть bigint, текущий тип: %', col_type;
    END IF;

    -- Проверка referral_links.referrer_tg_id
    SELECT data_type INTO col_type FROM information_schema.columns
    WHERE table_name = 'referral_links' AND column_name = 'referrer_tg_id';
    IF col_type != 'bigint' THEN
        RAISE EXCEPTION 'referral_links.referrer_tg_id должен быть bigint, текущий тип: %', col_type;
    END IF;

    -- Проверка referral_redemptions.referred_tg_id
    SELECT data_type INTO col_type FROM information_schema.columns
    WHERE table_name = 'referral_redemptions' AND column_name = 'referred_tg_id';
    IF col_type != 'bigint' THEN
        RAISE EXCEPTION 'referral_redemptions.referred_tg_id должен быть bigint, текущий тип: %', col_type;
    END IF;

    RAISE NOTICE 'Все поля tg_id имеют корректный тип bigint';
END $$;

COMMIT;
