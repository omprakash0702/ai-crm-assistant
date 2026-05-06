-- NOT NULL constraints
ALTER TABLE doctors         ALTER COLUMN user_id   SET NOT NULL;
ALTER TABLE interactions    ALTER COLUMN user_id   SET NOT NULL;
ALTER TABLE interactions    ALTER COLUMN doctor_id SET NOT NULL;

-- Indexes
CREATE INDEX IF NOT EXISTS idx_doctors_name_user   ON doctors     (LOWER(name), user_id);
CREATE INDEX IF NOT EXISTS idx_interactions_doctor ON interactions (doctor_id, created_at);
CREATE INDEX IF NOT EXISTS idx_interactions_user   ON interactions (user_id);
