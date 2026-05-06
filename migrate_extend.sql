-- Extended CRM data model: doctors + follow_up_tasks

CREATE TABLE IF NOT EXISTS doctors (
    id                  SERIAL PRIMARY KEY,
    name                VARCHAR(255) NOT NULL UNIQUE,
    last_visit          TIMESTAMP,
    total_interactions  INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS follow_up_tasks (
    id          SERIAL PRIMARY KEY,
    doctor_id   INTEGER REFERENCES doctors(id) ON DELETE CASCADE,
    task        TEXT NOT NULL,
    due_date    DATE,
    status      VARCHAR(50) DEFAULT 'pending'
);

ALTER TABLE interactions
ADD COLUMN IF NOT EXISTS doctor_id INTEGER REFERENCES doctors(id);
