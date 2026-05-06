CREATE TABLE IF NOT EXISTS llm_calls (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER REFERENCES users(id),
    model       VARCHAR(50) NOT NULL,
    latency_ms  FLOAT NOT NULL,
    cost_usd    DECIMAL(10, 8) NOT NULL DEFAULT 0,
    tokens_used INTEGER,
    created_at  TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_llm_calls_user_id    ON llm_calls(user_id);
CREATE INDEX IF NOT EXISTS idx_llm_calls_created_at ON llm_calls(created_at);
