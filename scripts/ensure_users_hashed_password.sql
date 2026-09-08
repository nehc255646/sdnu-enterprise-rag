-- Shared users table: chat service requires hashed_password.
-- Safe to run multiple times on Postgres 9.5+.
ALTER TABLE IF EXISTS users
  ADD COLUMN IF NOT EXISTS hashed_password VARCHAR(255);

UPDATE users
SET hashed_password = '!'
WHERE hashed_password IS NULL OR hashed_password = '';
