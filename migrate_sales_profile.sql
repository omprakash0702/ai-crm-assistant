ALTER TABLE users ADD COLUMN IF NOT EXISTS company   TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS job_title TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS territory TEXT;

-- JWT-registered users have no api_key, so the NOT NULL constraint must be relaxed
ALTER TABLE users ALTER COLUMN api_key DROP NOT NULL;
