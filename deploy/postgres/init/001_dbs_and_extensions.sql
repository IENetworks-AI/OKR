-- Init script to create OKR databases and core schemas
-- This runs in the default Postgres database on container init

DO $$
BEGIN
   PERFORM 1 FROM pg_database WHERE datname = 'okr_raw';
   IF NOT FOUND THEN
      EXECUTE 'CREATE DATABASE okr_raw';
   END IF;

   PERFORM 1 FROM pg_database WHERE datname = 'okr_processed';
   IF NOT FOUND THEN
      EXECUTE 'CREATE DATABASE okr_processed';
   END IF;

   PERFORM 1 FROM pg_database WHERE datname = 'okr_curated';
   IF NOT FOUND THEN
      EXECUTE 'CREATE DATABASE okr_curated';
   END IF;
END$$;

-- Basic role for application
DO $$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_roles WHERE rolname = 'okr_admin'
   ) THEN
      CREATE ROLE okr_admin LOGIN PASSWORD 'okr_password';
   END IF;
END$$;

-- Create schemas and tables in okr_raw
\connect okr_raw
CREATE SCHEMA IF NOT EXISTS public;
GRANT ALL PRIVILEGES ON SCHEMA public TO okr_admin;

CREATE TABLE IF NOT EXISTS public.files (
    file_id      BIGSERIAL PRIMARY KEY,
    path         TEXT NOT NULL,
    sha256       TEXT NOT NULL,
    rows         INTEGER NOT NULL DEFAULT 0,
    ingested_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.records (
    file_id      BIGINT NOT NULL REFERENCES public.files(file_id) ON DELETE CASCADE,
    row_num      INTEGER NOT NULL,
    payload      JSONB NOT NULL,
    loaded_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (file_id, row_num)
);

CREATE INDEX IF NOT EXISTS idx_files_sha256 ON public.files USING btree(sha256);
CREATE INDEX IF NOT EXISTS idx_files_ingested_at ON public.files USING btree(ingested_at);
CREATE INDEX IF NOT EXISTS idx_records_file_id ON public.records USING btree(file_id);
CREATE INDEX IF NOT EXISTS idx_records_payload_gin ON public.records USING gin(payload);

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO okr_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO okr_admin;

-- Create schemas and tables in okr_processed
\connect okr_processed
CREATE SCHEMA IF NOT EXISTS public;
GRANT ALL PRIVILEGES ON SCHEMA public TO okr_admin;

CREATE TABLE IF NOT EXISTS public.records_clean (
    record_id       BIGSERIAL PRIMARY KEY,
    source_file_id  BIGINT NOT NULL,
    row_num         INTEGER NOT NULL,
    data            JSONB NOT NULL,
    valid           BOOLEAN NOT NULL DEFAULT TRUE,
    rejected_reason TEXT NULL,
    processed_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_records_clean_source ON public.records_clean USING btree(source_file_id, row_num);
CREATE INDEX IF NOT EXISTS idx_records_clean_processed_at ON public.records_clean USING btree(processed_at);
CREATE INDEX IF NOT EXISTS idx_records_clean_data_gin ON public.records_clean USING gin(data);

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO okr_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO okr_admin;

-- Create schemas, extensions and tables in okr_curated
\connect okr_curated
CREATE SCHEMA IF NOT EXISTS public;
GRANT ALL PRIVILEGES ON SCHEMA public TO okr_admin;

-- Enable pgvector only in okr_curated
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS public.documents (
    doc_id     BIGSERIAL PRIMARY KEY,
    source     TEXT NOT NULL,
    text       TEXT NOT NULL,
    meta       JSONB NOT NULL,
    embedding  VECTOR(768) NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_documents_created_at ON public.documents USING btree(created_at);
CREATE INDEX IF NOT EXISTS idx_documents_meta_gin ON public.documents USING gin(meta);

-- Prepare ivfflat index for future use (requires populated embeddings)
-- CREATE INDEX IF NOT EXISTS idx_documents_embedding_ivfflat ON public.documents USING ivfflat (embedding vector_l2_ops) WITH (lists = 100);

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO okr_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO okr_admin;

