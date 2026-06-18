-- ============================================================================
-- Миграция 012: Поля для лендинга Telegram-доступа
-- ============================================================================
-- Описание: Добавляет два nullable-поля в таблицу keys для поддержки
--           анонимных 24-часовых VPN-ключей с лендинга и их привязки
--           к Telegram-юзеру через /start landing_<uid>.
-- Приоритет: Требуется для лендинга
-- Идемпотентность: да (проверка information_schema)
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 1. keys.landing_uid — уникальный ID, связывающий ключ с подписанной кукой
--    лендинга. 64 hex-символа достаточно, индекс для быстрого поиска.
-- ----------------------------------------------------------------------------
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'keys' AND column_name = 'landing_uid') THEN
        ALTER TABLE keys ADD COLUMN landing_uid VARCHAR(64);
        RAISE NOTICE 'Добавлено поле keys.landing_uid';
    ELSE
        RAISE NOTICE 'Поле keys.landing_uid уже существует';
    END IF;
END $$;

-- Индекс для быстрого поиска ключа по landing_uid
CREATE INDEX IF NOT EXISTS idx_keys_landing_uid ON keys(landing_uid)
    WHERE landing_uid IS NOT NULL;

COMMENT ON COLUMN keys.landing_uid IS
    'Уникальный ID анонимного лендинг-ключа. NULL = ключ создан не через лендинг.';

-- ----------------------------------------------------------------------------
-- 2. keys.converted_tg_id — tg_id юзера, дошедшего до бота через
--    /start landing_<uid>. NULL = юзер не дошёл (ключ всё ещё анонимный
--    или истёк).
-- ----------------------------------------------------------------------------
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'keys' AND column_name = 'converted_tg_id') THEN
        ALTER TABLE keys ADD COLUMN converted_tg_id BIGINT;
        RAISE NOTICE 'Добавлено поле keys.converted_tg_id';
    ELSE
        RAISE NOTICE 'Поле keys.converted_tg_id уже существует';
    END IF;
END $$;

COMMENT ON COLUMN keys.converted_tg_id IS
    'tg_id юзера, дошедшего до бота по /start landing_<uid>. '
    'NULL = юзер не дошёл. ВРЕМЕННЫЙ КЛЮЧ НЕ ОТКЛЮЧАЕТСЯ — продолжает жить до 24ч.';

COMMIT;
