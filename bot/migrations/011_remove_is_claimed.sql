-- Migration 011: Remove is_claimed flag from referral_rewards
-- Reason: All rewards are immediately credited to balance, flag is never used
-- Date: 2026-06-13

-- Drop index that uses is_claimed (may not exist in some environments)
DROP INDEX IF EXISTS idx_referral_rewards_unclaimed;
DROP INDEX IF EXISTS idx_referral_rewards_claimed;

-- Remove the column (if exists)
ALTER TABLE referral_rewards DROP COLUMN IF EXISTS is_claimed;

-- Remove comment if exists
COMMENT ON COLUMN referral_rewards.is_claimed IS NULL;
