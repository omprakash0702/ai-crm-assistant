CREATE TABLE IF NOT EXISTS users (
    id      SERIAL PRIMARY KEY,
    name    TEXT NOT NULL,
    api_key TEXT UNIQUE NOT NULL
);

ALTER TABLE doctors         ADD COLUMN IF NOT EXISTS user_id INT REFERENCES users(id);
ALTER TABLE interactions    ADD COLUMN IF NOT EXISTS user_id INT REFERENCES users(id);
ALTER TABLE follow_up_tasks ADD COLUMN IF NOT EXISTS user_id INT REFERENCES users(id);
