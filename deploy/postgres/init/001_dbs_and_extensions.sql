-- Initialize OKR data platform databases and schemas
-- This script is idempotent when re-run manually; the Docker init only runs on first init.

-- Create application role
DO $$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_catalog.pg_roles WHERE rolname = 'okr_admin'
   ) THEN
      CREATE ROLE okr_admin LOGIN PASSWORD 'okr_password' SUPERUSER;
   END IF;
END $$;

-- Create databases if not exist
DO $$
BEGIN
   IF NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'okr_raw') THEN
      PERFORM dblink_exec('dbname=' || current_database(), 'CREATE DATABASE okr_raw OWNER okr_admin');
   END IF;
   IF NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'okr_processed') THEN
      PERFORM dblink_exec('dbname=' || current_database(), 'CREATE DATABASE okr_processed OWNER okr_admin');
   END IF;
   IF NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'okr_curated') THEN
      PERFORM dblink_exec('dbname=' || current_database(), 'CREATE DATABASE okr_curated OWNER okr_admin');
   END IF;
END $$ LANGUAGE plpgsql;

-- The above uses dblink_exec; ensure dblink exists in current DB
CREATE EXTENSION IF NOT EXISTS dblink;

-- okr_curated: enable pgvector
\connect okr_curated
CREATE EXTENSION IF NOT EXISTS vector;

-- okr_raw schema and tables
\connect okr_raw
CREATE TABLE IF NOT EXISTS public.files (
  file_id SERIAL PRIMARY KEY,
  path TEXT NOT NULL,
  sha256 TEXT NOT NULL,
  rows INTEGER NOT NULL DEFAULT 0,
  ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.records (
  file_id INTEGER NOT NULL REFERENCES public.files(file_id) ON DELETE CASCADE,
  row_num INTEGER NOT NULL,
  payload JSONB NOT NULL,
  loaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (file_id, row_num)
);

CREATE INDEX IF NOT EXISTS idx_files_sha256 ON public.files USING btree(sha256);
CREATE INDEX IF NOT EXISTS idx_files_ingested_at ON public.files USING btree(ingested_at);
CREATE INDEX IF NOT EXISTS idx_records_file_id ON public.records USING btree(file_id);
CREATE INDEX IF NOT EXISTS idx_records_payload_gin ON public.records USING gin(payload);

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO okr_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO okr_admin;

-- okr_processed schema and tables
\connect okr_processed
CREATE TABLE IF NOT EXISTS public.records_clean (
  record_id SERIAL PRIMARY KEY,
  source_file_id INTEGER NOT NULL,
  row_num INTEGER NOT NULL,
  valid BOOLEAN NOT NULL DEFAULT true,
  rejected_reason TEXT NULL,
  processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  -- normalized columns: flexible via JSONB for unknowns; add common ones
  data JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_records_clean_source ON public.records_clean USING btree(source_file_id, row_num);
CREATE INDEX IF NOT EXISTS idx_records_clean_processed_at ON public.records_clean USING btree(processed_at);
CREATE INDEX IF NOT EXISTS idx_records_clean_data_gin ON public.records_clean USING gin(data);

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO okr_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO okr_admin;

-- okr_curated schema and tables
\connect okr_curated
CREATE TABLE IF NOT EXISTS public.documents (
  doc_id SERIAL PRIMARY KEY,
  source TEXT NOT NULL,
  text TEXT NOT NULL,
  meta JSONB NOT NULL,
  embedding vector(768) NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_documents_created_at ON public.documents USING btree(created_at);
CREATE INDEX IF NOT EXISTS idx_documents_meta_gin ON public.documents USING gin(meta);

-- Prepare vector index (disabled until populated)
-- CREATE INDEX IF NOT EXISTS idx_documents_embedding ON public.documents USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO okr_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO okr_admin;

