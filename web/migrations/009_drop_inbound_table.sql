-- Migration 009: Drop the inbound table
--
-- The Inbound entity is being removed from the platform. Inbound selection is
-- no longer needed in the admin UI: available connections now come from the
-- 3x-UI panel filtered by AVAILABLE_CONNECTIONS in .env (see FormConnectionData).
--
-- The `keys.inbound_id` column is KEPT — it stores the 3x-UI panel inbound_id
-- (e.g. 11, 12), not the serial PK of the dropped `inbound` table. Migration 008
-- already dropped the invalid FK `keys.inbound_id -> inbound(inbound_id)`, so the
-- `inbound` table is now unreferenced and safe to drop.
--
-- Idempotent: does nothing if the table does not exist.

BEGIN;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables WHERE table_name = 'inbound'
    ) THEN
        DROP TABLE inbound;
        RAISE NOTICE 'Migration 009: dropped table inbound';
    ELSE
        RAISE NOTICE 'Migration 009: table inbound not present, nothing to drop';
    END IF;
END $$;

COMMIT;