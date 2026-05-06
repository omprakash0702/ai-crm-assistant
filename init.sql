-- Auto-run by Postgres on first container start (docker-entrypoint-initdb.d)
-- Order matters: tables must exist before FK columns are added to them.

-- 1. Base interactions table
CREATE TABLE IF NOT EXISTS interactions (
    id          SERIAL PRIMARY KEY,
    doctor_name TEXT NOT NULL,
    notes       TEXT,
    created_at  TIMESTAMP DEFAULT NOW()
);

-- 2. Doctors + follow-up tasks; link doctor_id into interactions
CREATE TABLE IF NOT EXISTS doctors (
    id                 SERIAL PRIMARY KEY,
    name               VARCHAR(255) NOT NULL UNIQUE,
    last_visit         TIMESTAMP,
    total_interactions INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS follow_up_tasks (
    id        SERIAL PRIMARY KEY,
    doctor_id INTEGER REFERENCES doctors(id) ON DELETE CASCADE,
    task      TEXT NOT NULL,
    due_date  DATE,
    status    VARCHAR(50) DEFAULT 'pending'
);

ALTER TABLE interactions ADD COLUMN IF NOT EXISTS doctor_id INTEGER REFERENCES doctors(id);

-- 3. Users table; add user_id FK to all three tables
CREATE TABLE IF NOT EXISTS users (
    id             SERIAL PRIMARY KEY,
    name           TEXT NOT NULL,
    api_key        TEXT UNIQUE
);

ALTER TABLE doctors         ADD COLUMN IF NOT EXISTS user_id INT REFERENCES users(id);
ALTER TABLE interactions    ADD COLUMN IF NOT EXISTS user_id INT REFERENCES users(id);
ALTER TABLE follow_up_tasks ADD COLUMN IF NOT EXISTS user_id INT REFERENCES users(id);

-- 4. Extra interaction columns
ALTER TABLE interactions ADD COLUMN IF NOT EXISTS interaction_type  TEXT DEFAULT 'Meeting';
ALTER TABLE interactions ADD COLUMN IF NOT EXISTS attendees         TEXT;
ALTER TABLE interactions ADD COLUMN IF NOT EXISTS products_discussed TEXT;
ALTER TABLE interactions ADD COLUMN IF NOT EXISTS sentiment         TEXT DEFAULT 'Neutral';
ALTER TABLE interactions ADD COLUMN IF NOT EXISTS follow_up         TEXT;
ALTER TABLE interactions ADD COLUMN IF NOT EXISTS date_time         TEXT;

-- 5. JWT auth columns on users
ALTER TABLE users ADD COLUMN IF NOT EXISTS email           VARCHAR(255) UNIQUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS hashed_password TEXT;

-- 6. Sales profile columns on users
ALTER TABLE users ADD COLUMN IF NOT EXISTS company   TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS job_title TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS territory TEXT;

-- 7. LLM call log
CREATE TABLE IF NOT EXISTS llm_calls (
    id         SERIAL PRIMARY KEY,
    user_id    INTEGER REFERENCES users(id),
    model      VARCHAR(50) NOT NULL,
    latency_ms FLOAT NOT NULL,
    cost_usd   DECIMAL(10, 8) NOT NULL DEFAULT 0,
    tokens_used INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 8. Indexes and NOT NULL constraints (safe on empty tables)
ALTER TABLE doctors         ALTER COLUMN user_id   SET NOT NULL;
ALTER TABLE interactions    ALTER COLUMN user_id   SET NOT NULL;
ALTER TABLE interactions    ALTER COLUMN doctor_id SET NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_doctors_name_user ON doctors (LOWER(name), user_id);
CREATE INDEX IF NOT EXISTS idx_interactions_doctor  ON interactions (doctor_id, created_at);
CREATE INDEX IF NOT EXISTS idx_interactions_user    ON interactions (user_id);
CREATE INDEX IF NOT EXISTS idx_llm_calls_user_id    ON llm_calls    (user_id);
CREATE INDEX IF NOT EXISTS idx_llm_calls_created_at ON llm_calls    (created_at);
