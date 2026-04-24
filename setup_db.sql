-- Run this once in psql to create the table
-- psql -U postgres -d crm_db -f setup_db.sql

CREATE TABLE IF NOT EXISTS interactions (
    id          SERIAL PRIMARY KEY,
    doctor_name TEXT NOT NULL,
    notes       TEXT,
    created_at  TIMESTAMP DEFAULT NOW()
);
