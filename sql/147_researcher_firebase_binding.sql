-- Phase 4: Firebase identity binding on platform.researcher
CREATE SCHEMA IF NOT EXISTS platform;

ALTER TABLE platform.researcher
    ADD COLUMN IF NOT EXISTS firebase_uid text,
    ADD COLUMN IF NOT EXISTS email text;

CREATE UNIQUE INDEX IF NOT EXISTS idx_researcher_firebase_uid
    ON platform.researcher (firebase_uid)
    WHERE firebase_uid IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_researcher_email_lower
    ON platform.researcher (lower(email))
    WHERE email IS NOT NULL;

-- Best-effort backfill for rows created before Firebase binding
UPDATE platform.researcher
SET email = lower(username) || '@legacy.local'
WHERE email IS NULL
  AND username IS NOT NULL
  AND position('@' in username) = 0;
