-- Миграция: жизненный цикл статуса платежа
-- pending → succeeded → canceled

ALTER TABLE payments ALTER COLUMN status SET DEFAULT 'pending';
UPDATE payments SET status = 'succeeded' WHERE status = 'success';
