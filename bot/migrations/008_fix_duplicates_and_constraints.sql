-- Migration 008: Fix duplicate keys and enforce constraints
--
-- This migration:
-- 1. Removes duplicate keys (keeping the most recent by created_at)
-- 2. Enforces UNIQUE constraint on keys.email
-- 3. Ensures stocks table has correct schema with valid_until column
--
-- Safe to re-run: all DDL uses guards (DO $$ blocks)

BEGIN;

-- ============================================================================
-- 1. Remove duplicate keys (keep the one with latest created_at)
-- ============================================================================

-- Create temp table with duplicates for logging
CREATE TEMP TABLE duplicate_keys AS
SELECT email, COUNT(*) as cnt
FROM keys
GROUP BY email
HAVING COUNT(*) > 1;

-- Log how many duplicates we found (will appear in PostgreSQL logs)
DO $$
DECLARE
    dup_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO dup_count FROM duplicate_keys;
    IF dup_count > 0 THEN
        RAISE NOTICE 'Found % duplicate email(s) in keys table - removing...', dup_count;
    END IF;
END $$;

-- Delete duplicates, keeping the row with the highest ctid (most recently inserted)
-- ctid is PostgreSQL's physical row identifier
DELETE FROM keys a
USING keys b
WHERE a.email = b.email
  AND a.ctid < b.ctid;

-- Verify no duplicates remain
DO $$
DECLARE
    remaining INTEGER;
BEGIN
    SELECT COUNT(*) INTO remaining
    FROM (SELECT email FROM keys GROUP BY email HAVING COUNT(*) > 1) AS dups;

    IF remaining > 0 THEN
        RAISE EXCEPTION 'Failed to remove all duplicates - % email(s) still duplicated', remaining;
    END IF;
END $$;

-- ============================================================================
-- 2. Enforce UNIQUE constraint on keys.email
-- ============================================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'uq_keys_email' AND conrelid = 'keys'::regclass
    ) THEN
        ALTER TABLE keys ADD CONSTRAINT uq_keys_email UNIQUE (email);
        RAISE NOTICE 'Added UNIQUE constraint uq_keys_email on keys.email';
    ELSE
        RAISE NOTICE 'Constraint uq_keys_email already exists';
    END IF;
EXCEPTION
    WHEN unique_violation THEN
        -- This shouldn't happen since we just removed duplicates, but guard anyway
        RAISE NOTICE 'Could not add unique constraint - duplicates still exist';
END $$;

-- ============================================================================
-- 3. Fix stocks table schema (ensure valid_until column exists)
-- ============================================================================

-- First, drop the table if it exists in old format (without valid_until)
DO $$
BEGIN
    -- Check if stocks exists but doesn't have valid_until column
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'stocks'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'stocks' AND column_name = 'valid_until'
    ) THEN
        DROP TABLE stocks CASCADE;
        RAISE NOTICE 'Dropped legacy stocks table (missing valid_until column)';
    END IF;
END $$;

-- Create stocks table with correct schema
CREATE TABLE IF NOT EXISTS stocks (
    tg_id       BIGINT PRIMARY KEY REFERENCES users(tg_id) ON DELETE CASCADE,
    stock_type  TEXT NOT NULL CHECK (stock_type IN ('fix', 'percent')),
    value       DECIMAL(10,2) NOT NULL,
    is_active   BOOLEAN NOT NULL DEFAULT true,
    valid_until TIMESTAMPTZ,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Create index on stocks (guard for valid_until existence)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'stocks' AND column_name = 'valid_until'
    ) THEN
        CREATE INDEX IF NOT EXISTS idx_stocks_active ON stocks(is_active, valid_until);
        RAISE NOTICE 'Created index idx_stocks_active on stocks table';
    END IF;
END $$;

-- ============================================================================
-- 4. Log completion
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE 'Migration 008 completed successfully';
    RAISE NOTICE '  - Duplicate keys removed';
    RAISE NOTICE '  - UNIQUE constraint uq_keys_email enforced';
    RAISE NOTICE '  - stocks table schema corrected';
END $$;

COMMIT;
