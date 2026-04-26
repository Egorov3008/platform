-- Migration: Добавить поле discount_percent в таблицу payments
-- Фиксирует процент скидки за объём, применённый при оплате

ALTER TABLE payments ADD COLUMN IF NOT EXISTS discount_percent INTEGER NOT NULL DEFAULT 0;
