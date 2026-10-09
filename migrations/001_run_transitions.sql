BEGIN;

ALTER TABLE runs
    ADD COLUMN IF NOT EXISTS current_floor integer NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS room_completed boolean NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS pending_levels integer[] NOT NULL DEFAULT ARRAY[]::integer[],
    ADD COLUMN IF NOT EXISTS card_choices text[] NOT NULL DEFAULT ARRAY[]::text[],
    ADD COLUMN IF NOT EXISTS state_id uuid NOT NULL DEFAULT gen_random_uuid();

COMMIT;
