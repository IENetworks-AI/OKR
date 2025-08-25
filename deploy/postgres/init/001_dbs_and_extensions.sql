/*
Initial PostgreSQL setup for OKR data ingestion pipeline.
Creates dedicated databases, schemas, tables, extensions and indexes.
This script is idempotent and can be safely re-run.
*/

-- 1. Create required databases -------------------------------------------------
DO
$$
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

-- 2. Enable pgvector extension in okr_curated ---------------------------------
\connect okr_curated;
CREATE EXTENSION IF NOT EXISTS pgvector;

-- 3. Table definitions ---------------------------------------------------------
-- Raw layer --------------------------------------------------------------------
\connect okr_raw;

CREATE TABLE IF NOT EXISTS public.files (
    file_id     SERIAL PRIMARY KEY,
    path        TEXT NOT NULL UNIQUE,
    sha256      TEXT NOT NULL,
    rows        INTEGER NOT NULL,
    ingested_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.records (
    file_id     INTEGER REFERENCES public.files(file_id) ON DELETE CASCADE,
    row_num     INTEGER NOT NULL,
    payload     JSONB NOT NULL,
    loaded_at   TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (file_id, row_num)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_records_file_id ON public.records USING BTREE(file_id);
CREATE INDEX IF NOT EXISTS idx_records_loaded_at ON public.records USING BTREE(loaded_at);
CREATE INDEX IF NOT EXISTS idx_records_payload_gin ON public.records USING GIN(payload);

-- Processed layer --------------------------------------------------------------
\connect okr_processed;

CREATE TABLE IF NOT EXISTS public.records_clean (
    record_id        SERIAL PRIMARY KEY,
    source_file_id   INTEGER NOT NULL,
    row_num          INTEGER NOT NULL,
    valid            BOOLEAN NOT NULL,
    cleaned_payload  JSONB NOT NULL,
    rejected_reason  TEXT,
    processed_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_records_clean_source_file ON public.records_clean USING BTREE(source_file_id);
CREATE INDEX IF NOT EXISTS idx_records_clean_processed_at ON public.records_clean USING BTREE(processed_at);
CREATE INDEX IF NOT EXISTS idx_records_clean_payload_gin ON public.records_clean USING GIN(cleaned_payload);

-- Curated layer ----------------------------------------------------------------
\connect okr_curated;

CREATE TABLE IF NOT EXISTS public.documents (
    doc_id      SERIAL PRIMARY KEY,
    source      JSONB NOT NULL, -- {file_id, row_num}
    text        TEXT NOT NULL,
    meta        JSONB,
    embedding   VECTOR(768), -- may remain NULL until populated
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_documents_created_at ON public.documents USING BTREE(created_at);
CREATE INDEX IF NOT EXISTS idx_documents_meta_gin ON public.documents USING GIN(meta);
-- CREATE INDEX IF NOT EXISTS idx_documents_embedding ON public.documents USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100); -- Uncomment after vectors populated

-- End of script