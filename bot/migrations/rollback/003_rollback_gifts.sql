-- ============================================================================
-- Откат миграции 003: Откат миграции таблицы gifts
-- ============================================================================
-- Описание: Восстанавливает исходную структуру таблицы gifts
-- Внимание: Данные могут быть потеряны, если использовались новые поля
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- Шаг 1: Восстанавливаем старые поля (если были удалены)
-- ----------------------------------------------------------------------------

-- selected_months
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'gifts' AND column_name = 'selected_months') THEN
        ALTER TABLE gifts ADD COLUMN selected_months INTEGER;
        RAISE NOTICE 'Восстановлено поле gifts.selected_months';
    ELSE
        RAISE NOTICE 'Поле gifts.selected_months уже существует';
    END IF;
END $$;

-- gift_link
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'gifts' AND column_name = 'gift_link') THEN
        ALTER TABLE gifts ADD COLUMN gift_link TEXT;
        RAISE NOTICE 'Восстановлено поле gifts.gift_link';
    ELSE
        RAISE NOTICE 'Поле gifts.gift_link уже существует';
    END IF;
END $$;

-- is_used
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'gifts' AND column_name = 'is_used') THEN
        ALTER TABLE gifts ADD COLUMN is_used BOOLEAN NOT NULL DEFAULT FALSE;
        RAISE NOTICE 'Восстановлено поле gifts.is_used';
    ELSE
        RAISE NOTICE 'Поле gifts.is_used уже существует';
    END IF;
END $$;

-- expiry_time
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'gifts' AND column_name = 'expiry_time') THEN
        ALTER TABLE gifts ADD COLUMN expiry_time TIMESTAMP WITH TIME ZONE;
        RAISE NOTICE 'Восстановлено поле gifts.expiry_time';
    ELSE
        RAISE NOTICE 'Поле gifts.expiry_time уже существует';
    END IF;
END $$;

-- ----------------------------------------------------------------------------
-- Шаг 2: Обратная миграция данных
-- ----------------------------------------------------------------------------

-- tariff_id → selected_months
UPDATE gifts 
SET selected_months = tariff_id 
WHERE selected_months IS NULL AND tariff_id IS NOT NULL;

-- token → gift_link
UPDATE gifts 
SET gift_link = token 
WHERE gift_link IS NULL AND token IS NOT NULL;

-- used_at → is_used
UPDATE gifts 
SET is_used = TRUE 
WHERE used_at IS NOT NULL;

DO $$
BEGIN
    RAISE NOTICE 'Данные мигрированы обратно в старые поля';
END $$;

-- ----------------------------------------------------------------------------
-- Шаг 3: Удаляем новые поля и ограничения
-- ----------------------------------------------------------------------------

-- Снимаем ограничения UNIQUE
ALTER TABLE gifts DROP CONSTRAINT IF EXISTS gifts_token_key;

-- Удаляем FK
ALTER TABLE gifts DROP CONSTRAINT IF EXISTS fk_gifts_tariff;

-- Удаляем новые поля (раскомментировать если уверены)
-- ALTER TABLE gifts DROP COLUMN IF EXISTS tariff_id;
-- ALTER TABLE gifts DROP COLUMN IF EXISTS token;
-- ALTER TABLE gifts DROP COLUMN IF EXISTS email;
-- ALTER TABLE gifts DROP COLUMN IF EXISTS used_at;

DO $$
BEGIN
    RAISE NOTICE 'Новые поля сохранены (закомментировано DROP).';
    RAISE NOTICE 'Для удаления раскомментируйте DROP команды.';
END $$;

-- ----------------------------------------------------------------------------
-- Логирование
-- ----------------------------------------------------------------------------
DO $$
BEGIN
    RAISE NOTICE 'Откат миграции 003: Таблица gifts возвращена к исходной структуре';
END $$;

COMMIT;
