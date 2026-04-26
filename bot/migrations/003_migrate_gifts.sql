-- ============================================================================
-- Миграция 003: Миграция таблицы gifts
-- ============================================================================
-- Описание: Приводит таблицу gifts к структуре, соответствующей модели GiftLink
-- Проблема: В БД структура отличается от schema.sql и модели
-- 
-- В БД сейчас:
--   - gift_id TEXT (PK)
--   - selected_months INT
--   - gift_link TEXT
--   - is_used BOOL
-- 
-- Требуется (по модели GiftLink):
--   - id SERIAL (PK)
--   - tariff_id INT
--   - token TEXT
--   - email TEXT
--   - used_at TIMESTAMP
--   - recipient_tg_id BIGINT (уже есть)
--   - created_at TIMESTAMP (уже есть)
--   - sender_tg_id BIGINT (уже есть)
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- Шаг 1: Добавляем новые поля (если отсутствуют)
-- ----------------------------------------------------------------------------

-- tariff_id (вместо selected_months)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'gifts' AND column_name = 'tariff_id') THEN
        ALTER TABLE gifts ADD COLUMN tariff_id INTEGER;
        RAISE NOTICE 'Добавлено поле gifts.tariff_id';
    ELSE
        RAISE NOTICE 'Поле gifts.tariff_id уже существует';
    END IF;
END $$;

-- token (вместо gift_link)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'gifts' AND column_name = 'token') THEN
        ALTER TABLE gifts ADD COLUMN token TEXT;
        RAISE NOTICE 'Добавлено поле gifts.token';
    ELSE
        RAISE NOTICE 'Поле gifts.token уже существует';
    END IF;
END $$;

-- email
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'gifts' AND column_name = 'email') THEN
        ALTER TABLE gifts ADD COLUMN email TEXT;
        RAISE NOTICE 'Добавлено поле gifts.email';
    ELSE
        RAISE NOTICE 'Поле gifts.email уже существует';
    END IF;
END $$;

-- used_at (вместо is_used)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'gifts' AND column_name = 'used_at') THEN
        ALTER TABLE gifts ADD COLUMN used_at TIMESTAMP WITH TIME ZONE;
        RAISE NOTICE 'Добавлено поле gifts.used_at';
    ELSE
        RAISE NOTICE 'Поле gifts.used_at уже существует';
    END IF;
END $$;

-- ----------------------------------------------------------------------------
-- Шаг 2: Миграция данных
-- ----------------------------------------------------------------------------

-- 2.1: Копируем selected_months → tariff_id
-- Предполагаем, что selected_months соответствует ID тарифа (1, 2, 3 месяца)
-- Если тарифы имеют другую структуру, потребуется ручная маппинг
UPDATE gifts 
SET tariff_id = selected_months 
WHERE tariff_id IS NULL AND selected_months IS NOT NULL;

DO $$
DECLARE
    updated_count INTEGER;
BEGIN
    GET DIAGNOSTICS updated_count = ROW_COUNT;
    RAISE NOTICE 'Мигрировано записей gifts.tariff_id: %', updated_count;
END $$;

-- 2.2: Копируем gift_link → token
UPDATE gifts 
SET token = gift_link 
WHERE token IS NULL AND gift_link IS NOT NULL;

DO $$
DECLARE
    updated_count INTEGER;
BEGIN
    GET DIAGNOSTICS updated_count = ROW_COUNT;
    RAISE NOTICE 'Мигрировано записей gifts.token: %', updated_count;
END $$;

-- 2.3: Конвертируем is_used → used_at
-- Если is_used = TRUE, устанавливаем used_at = created_at (или текущее время)
UPDATE gifts 
SET used_at = created_at 
WHERE used_at IS NULL AND is_used = TRUE;

DO $$
DECLARE
    updated_count INTEGER;
BEGIN
    GET DIAGNOSTICS updated_count = ROW_COUNT;
    RAISE NOTICE 'Мигрировано записей gifts.used_at: %', updated_count;
END $$;

-- ----------------------------------------------------------------------------
-- Шаг 3: Добавляем ограничения
-- ----------------------------------------------------------------------------

-- Делаем tariff_id NOT NULL (после миграции данных)
ALTER TABLE gifts ALTER COLUMN tariff_id SET NOT NULL;

-- Делаем token NOT NULL и добавляем UNIQUE
ALTER TABLE gifts ALTER COLUMN token SET NOT NULL;
ALTER TABLE gifts ADD CONSTRAINT gifts_token_key UNIQUE (token);

-- Добавляем FK для tariff_id
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.constraint_column_usage 
                   WHERE table_name = 'gifts' AND constraint_name = 'fk_gifts_tariff') THEN
        ALTER TABLE gifts 
        ADD CONSTRAINT fk_gifts_tariff 
        FOREIGN KEY (tariff_id) REFERENCES tariff(id) ON DELETE RESTRICT;
        RAISE NOTICE 'Добавлен FK gifts.tariff_id -> tariff.id';
    END IF;
END $$;

-- ----------------------------------------------------------------------------
-- Шаг 4: Миграция gift_redemptions
-- ----------------------------------------------------------------------------
-- В БД: recipient_tg_id, gift_link_id, used_at, email
-- В модели: referred_tg_id, referral_link_id, redeemed_at
-- 
-- Решение: Оставить как есть, т.к. gift_redemptions связана с gift_links,
-- а не с referral_links. Это отдельная сущность для подарков.

-- Проверяем структуру gift_redemptions
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'gift_redemptions' AND column_name = 'email') THEN
        RAISE NOTICE 'gift_redemptions.email существует (оставляем для совместимости)';
    END IF;
END $$;

-- ----------------------------------------------------------------------------
-- Шаг 5: Очистка старых полей (опционально, можно закомментировать)
-- ----------------------------------------------------------------------------
-- Раскомментировать, если уверены, что данные перенесены корректно

-- ALTER TABLE gifts DROP COLUMN IF EXISTS selected_months;
-- ALTER TABLE gifts DROP COLUMN IF EXISTS gift_link;
-- ALTER TABLE gifts DROP COLUMN IF EXISTS is_used;
-- ALTER TABLE gifts DROP COLUMN IF EXISTS expiry_time;

DO $$
BEGIN
    RAISE NOTICE 'Старые поля gifts сохранены (закомментировано DROP).';
    RAISE NOTICE 'Для удаления раскомментируйте DROP в миграции 003.';
END $$;

-- ----------------------------------------------------------------------------
-- Логирование применения миграции
-- ----------------------------------------------------------------------------
DO $$
BEGIN
    RAISE NOTICE 'Миграция 003: Таблица gifts приведена к модели GiftLink';
END $$;

COMMIT;
