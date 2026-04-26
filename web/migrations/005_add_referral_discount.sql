-- Add referral_discount column to payments table
ALTER TABLE payments ADD COLUMN IF NOT EXISTS referral_discount REAL DEFAULT 0.0;
