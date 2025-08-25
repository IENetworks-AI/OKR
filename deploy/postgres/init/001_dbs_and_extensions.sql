-- Initialize OKR PostgreSQL databases and schemas
-- Creates databases: okr_raw, okr_processed, okr_curated
-- Enables pgvector in okr_curated and creates required tables and indexes

\set ON_ERROR_STOP on

-- Roles
DO $$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_catalog.pg_roles WHERE rolname = 'okr_admin'
   ) THEN
      CREATE ROLE okr_admin LOGIN PASSWORD 'okr_password' SUPERUSER CREATEDB CREATEROLE INHERIT;
   END IF;
END
$$;

-- Databases
DO $$
BEGIN
   IF NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'okr_raw') THEN
      CREATE DATABASE okr_raw OWNER okr_admin;
   END IF;
   IF NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'okr_processed') THEN
      CREATE DATABASE okr_processed OWNER okr_admin;
   END IF;
   IF NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'okr_curated') THEN
      CREATE DATABASE okr_curated OWNER okr_admin;
   END IF;
END
$$;

-- okr_raw schema and tables
\connect okr_raw

CREATE SCHEMA IF NOT EXISTS public;

CREATE TABLE IF NOT EXISTS public.files (
    file_id      BIGSERIAL PRIMARY KEY,
    path         TEXT NOT NULL,
    sha256       TEXT NOT NULL,
    rows         INTEGER NOT NULL DEFAULT 0,
    ingested_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_files_path_sha ON public.files (path, sha256);
CREATE INDEX IF NOT EXISTS idx_files_ingested_at ON public.files (ingested_at);

CREATE TABLE IF NOT EXISTS public.records (
    file_id    BIGINT NOT NULL REFERENCES public.files(file_id) ON DELETE CASCADE,
    row_num    INTEGER NOT NULL,
    payload    JSONB NOT NULL,
    loaded_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (file_id, row_num)
);

CREATE INDEX IF NOT EXISTS idx_records_file_id ON public.records (file_id);
CREATE INDEX IF NOT EXISTS idx_records_loaded_at ON public.records (loaded_at);
CREATE INDEX IF NOT EXISTS idx_records_payload_gin ON public.records USING GIN (payload);

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO okr_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO okr_admin;

-- okr_processed schema and tables
\connect okr_processed

CREATE SCHEMA IF NOT EXISTS public;

CREATE TABLE IF NOT EXISTS public.records_clean (
    record_id        BIGSERIAL PRIMARY KEY,
    source_file_id   BIGINT NOT NULL,
    row_num          INTEGER NOT NULL,
    data             JSONB NOT NULL,
    valid            BOOLEAN NOT NULL DEFAULT true,
    rejected_reason  TEXT NULL,
    processed_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Ensure idempotent upserts via unique constraint on (source_file_id, row_num)
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'uq_records_clean_source_row'
    ) THEN
        ALTER TABLE public.records_clean
        ADD CONSTRAINT uq_records_clean_source_row UNIQUE (source_file_id, row_num);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_records_clean_source ON public.records_clean (source_file_id, row_num);
CREATE INDEX IF NOT EXISTS idx_records_clean_processed_at ON public.records_clean (processed_at);
CREATE INDEX IF NOT EXISTS idx_records_clean_data_gin ON public.records_clean USING GIN (data);

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO okr_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO okr_admin;

-- okr_curated schema and tables
\connect okr_curated

CREATE SCHEMA IF NOT EXISTS public;

-- Enable pgvector (vector) extension for embeddings if available
DO $$
BEGIN
   IF EXISTS (
      SELECT 1 FROM pg_available_extensions WHERE name IN ('vector', 'pgvector')
   ) THEN
      BEGIN
         EXECUTE 'CREATE EXTENSION IF NOT EXISTS vector';
      EXCEPTION WHEN OTHERS THEN
         -- Some distributions name it pgvector
         EXECUTE 'CREATE EXTENSION IF NOT EXISTS pgvector';
      END;
   END IF;
END$$;

-- Create documents table without embedding column first to avoid type dependency
CREATE TABLE IF NOT EXISTS public.documents (
    doc_id     BIGSERIAL PRIMARY KEY,
    source     TEXT NOT NULL,
    text       TEXT NOT NULL,
    meta       JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Conditionally add embedding column of type vector(768) if extension is available
DO $$
BEGIN
   IF EXISTS (
      SELECT 1 FROM pg_type WHERE typname = 'vector'
   ) THEN
      IF NOT EXISTS (
         SELECT 1 FROM information_schema.columns
         WHERE table_schema = 'public' AND table_name = 'documents' AND column_name = 'embedding'
      ) THEN
         EXECUTE 'ALTER TABLE public.documents ADD COLUMN embedding vector(768) NULL';
      END IF;
   END IF;
END$$;

CREATE INDEX IF NOT EXISTS idx_documents_created_at ON public.documents (created_at);
CREATE INDEX IF NOT EXISTS idx_documents_meta_gin ON public.documents USING GIN (meta);

-- Example vector index (prepare but keep commented until embeddings are populated)
-- CREATE INDEX IF NOT EXISTS idx_documents_embedding ON public.documents USING ivfflat (embedding vector_l2_ops) WITH (lists = 100);

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO okr_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO okr_admin;

