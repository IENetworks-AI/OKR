-- Initialization script for OKR data platform databases and schemas
-- Creates databases: okr_raw, okr_processed, okr_curated
-- Enables pgvector (vector) extension in okr_curated
-- Creates core tables and useful indexes

\echo 'Creating OKR databases if they do not exist...'
SELECT 'CREATE DATABASE okr_raw' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'okr_raw')\gexec
SELECT 'CREATE DATABASE okr_processed' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'okr_processed')\gexec
SELECT 'CREATE DATABASE okr_curated' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'okr_curated')\gexec

\echo 'Enabling pgvector extension in okr_curated...'
\connect okr_curated
CREATE EXTENSION IF NOT EXISTS vector;

\echo 'Creating tables in okr_raw...'
\connect okr_raw

-- Raw files metadata
CREATE TABLE IF NOT EXISTS public.files (
    file_id     BIGSERIAL PRIMARY KEY,
    path        TEXT NOT NULL,
    sha256      TEXT NOT NULL,
    rows        INTEGER,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT files_path_sha256_uk UNIQUE (path, sha256)
);

-- Raw records stored losslessly as JSONB with row-level provenance
CREATE TABLE IF NOT EXISTS public.records (
    record_id   BIGSERIAL PRIMARY KEY,
    file_id     BIGINT NOT NULL REFERENCES public.files(file_id) ON DELETE CASCADE,
    row_num     INTEGER NOT NULL,
    payload     JSONB NOT NULL,
    loaded_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT records_file_row_uk UNIQUE (file_id, row_num)
);

-- Useful indexes for raw
CREATE INDEX IF NOT EXISTS idx_files_ingested_at ON public.files USING BTREE (ingested_at);
CREATE INDEX IF NOT EXISTS idx_records_file_id ON public.records USING BTREE (file_id);
CREATE INDEX IF NOT EXISTS idx_records_payload_gin ON public.records USING GIN (payload);

\echo 'Creating tables in okr_processed...'
\connect okr_processed

-- Cleaned/validated records; keep normalized cleaned JSON and flags
CREATE TABLE IF NOT EXISTS public.records_clean (
    record_id        BIGSERIAL PRIMARY KEY,
    source_file_id   BIGINT NOT NULL,
    row_num          INTEGER NOT NULL,
    cleaned          JSONB,
    valid            BOOLEAN NOT NULL DEFAULT FALSE,
    rejected_reason  TEXT,
    processed_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes for processed
CREATE INDEX IF NOT EXISTS idx_records_clean_source_file_id ON public.records_clean USING BTREE (source_file_id);
CREATE INDEX IF NOT EXISTS idx_records_clean_processed_at ON public.records_clean USING BTREE (processed_at);
CREATE INDEX IF NOT EXISTS idx_records_clean_cleaned_gin ON public.records_clean USING GIN (cleaned);

\echo 'Creating tables in okr_curated...'
\connect okr_curated

-- Final model-ready documents for fine-tuning and RAG
CREATE TABLE IF NOT EXISTS public.documents (
    doc_id     BIGSERIAL PRIMARY KEY,
    source     TEXT,
    text       TEXT NOT NULL,
    meta       JSONB,
    embedding  VECTOR(768), -- prepared for future use; can be NULL
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes for curated
CREATE INDEX IF NOT EXISTS idx_documents_created_at ON public.documents USING BTREE (created_at);
CREATE INDEX IF NOT EXISTS idx_documents_meta_gin ON public.documents USING GIN (meta);

-- Optional: Uncomment to prepare approximate nearest neighbor index once embeddings are populated
-- Requires pgvector >= 0.4.0
-- CREATE INDEX documents_embedding_ivfflat_idx ON public.documents USING ivfflat (embedding vector_l2_ops) WITH (lists = 100);

\echo 'Granting minimal privileges...'
-- Minimal roles and privileges (optional; adapt as needed)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'okr_ro') THEN
        CREATE ROLE okr_ro;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'okr_rw') THEN
        CREATE ROLE okr_rw;
    END IF;
END$$;

GRANT USAGE ON SCHEMA public TO okr_ro, okr_rw;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO okr_ro;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO okr_rw;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO okr_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO okr_rw;

\echo 'OKR databases and tables initialized.'

