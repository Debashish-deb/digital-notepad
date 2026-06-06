-- Extend registration requests with organization (login page).

ALTER TABLE platform.registration_request
  ADD COLUMN IF NOT EXISTS organization text;
