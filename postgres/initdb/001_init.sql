-- Create schemas and enable pgvector
CREATE EXTENSION IF NOT EXISTS vector;

CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS curated;
CREATE SCHEMA IF NOT EXISTS analytics;

-- Basic role setup
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT FROM pg_roles WHERE rolname = 'app_writer'
  ) THEN
    CREATE ROLE app_writer LOGIN PASSWORD 'okr_password';
    GRANT CONNECT ON DATABASE okr TO app_writer;
    GRANT USAGE ON SCHEMA staging, curated, analytics TO app_writer;
    GRANT CREATE, USAGE ON SCHEMA staging TO app_writer;
  END IF;
END$$;

