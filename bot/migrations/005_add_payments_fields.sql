-- ============================================================================
-- Миграция 005: Добавление полей в таблицу payments
-- ============================================================================
-- Описание: Добавляет отсутствующие поля number_of_months и discount_percent
-- Проблема: Ошибка UndefinedColumnError при создании платежа
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 1. Добавляем поле number_of_months
-- ----------------------------------------------------------------------------
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'payments' AND column_name = 'number_of_months') THEN
        ALTER TABLE payments ADD COLUMN number_of_months INTEGER NOT NULL DEFAULT 1;
        RAISE NOTICE 'Добавлено поле payments.number_of_months';
    ELSE
        RAISE NOTICE 'Поле payments.number_of_months уже существует';
    END IF;
END $$;

COMMENT ON COLUMN payments.number_of_months IS 'Количество месяцев подписки';

-- ----------------------------------------------------------------------------
-- 2. Добавляем поле discount_percent
-- ----------------------------------------------------------------------------
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'payments' AND column_name = 'discount_percent') THEN
        ALTER TABLE payments ADD COLUMN discount_percent INTEGER NOT NULL DEFAULT 0;
        RAISE NOTICE 'Добавлено поле payments.discount_percent';
    ELSE
        RAISE NOTICE 'Поле payments.discount_percent уже существует';
    END IF;
END $$;

COMMENT ON COLUMN payments.discount_percent IS 'Процент скидки за объём (0 если без скидки)';

-- ----------------------------------------------------------------------------
-- Логирование применения миграции
-- ----------------------------------------------------------------------------
DO $$
BEGIN
    RAISE NOTICE 'Миграция 005: Добавлены поля в таблицу payments';
END $$;

COMMIT;
