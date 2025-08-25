-- Initialize OKR data warehouses inside a single Postgres instance
-- Databases: okr_raw, okr_processed, okr_curated
-- Extensions: pgvector enabled only in okr_curated

\connect postgres

DO $$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_database WHERE datname = 'okr_raw'
   ) THEN
      PERFORM dblink_exec('dbname=' || current_database(), 'CREATE DATABASE okr_raw');
   END IF;
EXCEPTION WHEN undefined_table THEN
   -- dblink may not be available; fallback to CREATE DATABASE guarded by exception
   BEGIN
      CREATE DATABASE okr_raw;
   EXCEPTION WHEN duplicate_database THEN
      -- ignore
   END;
END$$;

DO $$
BEGIN
   BEGIN
      CREATE DATABASE okr_processed;
   EXCEPTION WHEN duplicate_database THEN
      -- ignore
   END;
END$$;

DO $$
BEGIN
   BEGIN
      CREATE DATABASE okr_curated;
   EXCEPTION WHEN duplicate_database THEN
      -- ignore
   END;
END$$;

-- Minimal role for application
DO $$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'okr_admin') THEN
      CREATE ROLE okr_admin LOGIN PASSWORD 'okr_password';
   END IF;
END$$;

-- Raw DB schema
\connect okr_raw
CREATE SCHEMA IF NOT EXISTS public;
GRANT ALL PRIVILEGES ON SCHEMA public TO okr_admin;

CREATE TABLE IF NOT EXISTS public.files (
  file_id      BIGSERIAL PRIMARY KEY,
  path         TEXT NOT NULL,
  sha256       TEXT NOT NULL,
  rows         INTEGER NOT NULL,
  ingested_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_files_sha256 ON public.files(sha256);
CREATE INDEX IF NOT EXISTS idx_files_sha256 ON public.files USING btree (sha256);
CREATE INDEX IF NOT EXISTS idx_files_ingested_at ON public.files USING btree (ingested_at);

CREATE TABLE IF NOT EXISTS public.records (
  file_id    BIGINT NOT NULL REFERENCES public.files(file_id) ON DELETE CASCADE,
  row_num    INTEGER NOT NULL,
  payload    JSONB NOT NULL,
  loaded_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (file_id, row_num)
);
CREATE INDEX IF NOT EXISTS idx_records_file_id ON public.records USING btree (file_id);
CREATE INDEX IF NOT EXISTS idx_records_loaded_at ON public.records USING btree (loaded_at);
CREATE INDEX IF NOT EXISTS idx_records_payload_gin ON public.records USING GIN (payload);

GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO okr_admin;

-- Processed DB schema
\connect okr_processed
CREATE SCHEMA IF NOT EXISTS public;
GRANT ALL PRIVILEGES ON SCHEMA public TO okr_admin;

CREATE TABLE IF NOT EXISTS public.records_clean (
  record_id        BIGSERIAL PRIMARY KEY,
  source_file_id   BIGINT NOT NULL,
  row_num          INTEGER NOT NULL,
  valid            BOOLEAN NOT NULL DEFAULT TRUE,
  rejected_reason  TEXT NULL,
  cols             JSONB NOT NULL,
  processed_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_records_clean_source ON public.records_clean USING btree (source_file_id);
CREATE INDEX IF NOT EXISTS idx_records_clean_processed_at ON public.records_clean USING btree (processed_at);
CREATE INDEX IF NOT EXISTS idx_records_clean_cols_gin ON public.records_clean USING GIN (cols);

GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO okr_admin;

-- Curated DB schema
\connect okr_curated
CREATE SCHEMA IF NOT EXISTS public;
GRANT ALL PRIVILEGES ON SCHEMA public TO okr_admin;

-- Enable pgvector only here
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS public.documents (
  doc_id     BIGSERIAL PRIMARY KEY,
  source     TEXT NOT NULL,
  text       TEXT NOT NULL,
  meta       JSONB NOT NULL,
  embedding  VECTOR(768) NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_documents_created_at ON public.documents USING btree (created_at);
CREATE INDEX IF NOT EXISTS idx_documents_meta_gin ON public.documents USING GIN (meta);

-- Optional: prepare IVFFLAT index (requires populated embeddings and appropriate lists)
-- CREATE INDEX IF NOT EXISTS idx_documents_embedding_ivfflat ON public.documents USING ivfflat (embedding vector_l2_ops) WITH (lists = 100);

GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO okr_admin;

