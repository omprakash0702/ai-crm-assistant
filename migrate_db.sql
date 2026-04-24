-- Run once to add new columns to the interactions table
-- psql -U postgres -d crm_db -f migrate_db.sql

ALTER TABLE interactions ADD COLUMN IF NOT EXISTS interaction_type TEXT DEFAULT 'Meeting';
ALTER TABLE interactions ADD COLUMN IF NOT EXISTS attendees TEXT;
ALTER TABLE interactions ADD COLUMN IF NOT EXISTS products_discussed TEXT;
ALTER TABLE interactions ADD COLUMN IF NOT EXISTS sentiment TEXT DEFAULT 'Neutral';
ALTER TABLE interactions ADD COLUMN IF NOT EXISTS follow_up TEXT;
ALTER TABLE interactions ADD COLUMN IF NOT EXISTS date_time TEXT;
