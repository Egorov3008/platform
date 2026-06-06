-- ============================================================================
-- Миграция 006: Добавление поля referral_discount в таблицу payments
-- ============================================================================
-- Описание: Добавляет поле referral_discount, отсутствующее в существующих БД
-- Проблема: INSERT падает с "column referral_discount does not exist" при создании
--           платежа, потому что миграция 005 не включала это поле
-- Контекст: backend/models/payments/payment.py включает referral_discount в
--           _DB_FIELDS и to_dict() всегда его вставляет
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 1. Добавляем поле referral_discount (если ещё не существует)
-- ----------------------------------------------------------------------------
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'payments' AND column_name = 'referral_discount') THEN
        ALTER TABLE payments ADD COLUMN referral_discount REAL NOT NULL DEFAULT 0.0;
        RAISE NOTICE 'Добавлено поле payments.referral_discount';
    ELSE
        RAISE NOTICE 'Поле payments.referral_discount уже существует';
    END IF;
END $$;

COMMENT ON COLUMN payments.referral_discount IS 'Сумма скидки по реферальной программе (в рублях)';

-- ----------------------------------------------------------------------------
-- Логирование применения миграции
-- ----------------------------------------------------------------------------
DO $$
BEGIN
    RAISE NOTICE 'Миграция 006: Добавлено поле payments.referral_discount';
END $$;

COMMIT;
