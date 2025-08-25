-- Initialize databases for OKR data platform
-- Run as part of Postgres container initialization.

-- 1. Create dedicated databases ------------------------------------------------
CREATE DATABASE okr_raw;
CREATE DATABASE okr_processed;
CREATE DATABASE okr_curated;

-- 2. Define schema in okr_raw ---------------------------------------------------
\connect okr_raw;

-- Table to register ingested files (one row per physical file ingested)
CREATE TABLE IF NOT EXISTS public.files (
    file_id        SERIAL PRIMARY KEY,
    path           TEXT        NOT NULL UNIQUE,
    sha256         CHAR(64)    NOT NULL,
    rows           INTEGER     NOT NULL,
    ingested_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Raw records preserved as-is (row-level fidelity)
CREATE TABLE IF NOT EXISTS public.records (
    file_id     INTEGER     NOT NULL REFERENCES public.files(file_id) ON DELETE CASCADE,
    row_num     INTEGER     NOT NULL,
    payload     JSONB       NOT NULL,
    loaded_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (file_id, row_num)
);

-- Helpful indexes
CREATE INDEX IF NOT EXISTS idx_files_path       ON public.files USING btree(path);
CREATE INDEX IF NOT EXISTS idx_records_file_id  ON public.records USING btree(file_id);
CREATE INDEX IF NOT EXISTS idx_records_payload_gin ON public.records USING gin(payload);

-- 3. Define schema in okr_processed --------------------------------------------
\connect okr_processed;

-- Cleaned & validated records (add your domain-specific columns as needed)
-- The column list below is illustrative; adjust via migrations when schema evolves.
CREATE TABLE IF NOT EXISTS public.records_clean (
    record_id        SERIAL PRIMARY KEY,
    source_file_id   INTEGER NOT NULL,
    row_num          INTEGER NOT NULL,
    data             JSONB  NOT NULL,
    valid            BOOLEAN NOT NULL,
    rejected_reason  TEXT,
    processed_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_records_clean_source ON public.records_clean USING btree(source_file_id);
CREATE INDEX IF NOT EXISTS idx_records_clean_data_gin ON public.records_clean USING gin(data);

-- 4. Define schema in okr_curated ----------------------------------------------
\connect okr_curated;

-- Enable pgvector extension for future embeddings storage
CREATE EXTENSION IF NOT EXISTS "vector";

CREATE TABLE IF NOT EXISTS public.documents (
    doc_id      SERIAL PRIMARY KEY,
    source      TEXT        NOT NULL,
    text        TEXT        NOT NULL,
    meta        JSONB       NOT NULL,
    embedding   VECTOR(768), -- to be populated in downstream tasks
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for efficient retrieval
CREATE INDEX IF NOT EXISTS idx_documents_source        ON public.documents USING btree(source);
CREATE INDEX IF NOT EXISTS idx_documents_created_at    ON public.documents USING btree(created_at);
CREATE INDEX IF NOT EXISTS idx_documents_meta_gin      ON public.documents USING gin(meta);
-- Uncomment after vectors are populated & ANALYZE done: requires pgvector >=0.5
-- CREATE INDEX IF NOT EXISTS idx_documents_embedding_ivfflat ON public.documents USING ivfflat (embedding vector_cosine_ops);

-- 5. Grant minimal privileges ---------------------------------------------------
-- (Assuming default superuser creates DBs; adjust roles/privileges in prod)
GRANT CONNECT ON DATABASE okr_raw, okr_processed, okr_curated TO PUBLIC;