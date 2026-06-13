-- Rollback Migration 011: Re-add is_claimed flag to referral_rewards
-- Date: 2026-06-13

-- Re-add the column
ALTER TABLE referral_rewards ADD COLUMN IF NOT EXISTS is_claimed BOOLEAN DEFAULT FALSE;

-- Re-create the index
CREATE INDEX IF NOT EXISTS idx_referral_rewards_unclaimed ON referral_rewards(is_claimed) WHERE is_claimed = FALSE;

-- Add comment
COMMENT ON COLUMN referral_rewards.is_claimed IS 'Флаг получения награды';
