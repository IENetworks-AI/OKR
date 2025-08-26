
-- PostgreSQL initialization script for OKR ETL pipeline
-- Creates three databases: okr_raw, okr_processed, okr_curated
-- Sets up tables and extensions for data ingestion pipeline

-- Create databases

CREATE DATABASE okr_raw;
CREATE DATABASE okr_processed;
CREATE DATABASE okr_curated;

-- Create roles and users
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'okr_admin') THEN
        CREATE ROLE okr_admin WITH LOGIN PASSWORD 'okr_password';
    END IF;
END
$$;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE okr_raw TO okr_admin;
GRANT ALL PRIVILEGES ON DATABASE okr_processed TO okr_admin;
GRANT ALL PRIVILEGES ON DATABASE okr_curated TO okr_admin;

-- Connect to okr_raw database and create tables
\c okr_raw;

-- Files metadata table
CREATE TABLE IF NOT EXISTS public.files (
    file_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    path TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    rows INTEGER NOT NULL,
    ingested_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(path, sha256)
);

-- Raw records table (lossless storage as JSONB)
CREATE TABLE IF NOT EXISTS public.records (
    record_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_id UUID NOT NULL REFERENCES public.files(file_id) ON DELETE CASCADE,
    row_num INTEGER NOT NULL,
    payload JSONB NOT NULL,
    loaded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for okr_raw
CREATE INDEX IF NOT EXISTS idx_files_path ON public.files(path);
CREATE INDEX IF NOT EXISTS idx_files_ingested_at ON public.files(ingested_at);
CREATE INDEX IF NOT EXISTS idx_records_file_id ON public.records(file_id);
CREATE INDEX IF NOT EXISTS idx_records_row_num ON public.records(file_id, row_num);
CREATE INDEX IF NOT EXISTS idx_records_payload_gin ON public.records USING GIN(payload);
CREATE INDEX IF NOT EXISTS idx_records_loaded_at ON public.records(loaded_at);

-- Grant permissions on okr_raw
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO okr_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO okr_admin;

-- Connect to okr_processed database and create tables
\c okr_processed;

-- Processed records table (normalized schema)
CREATE TABLE IF NOT EXISTS public.records_clean (
    record_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_file_id UUID NOT NULL,
    source_row_num INTEGER NOT NULL,
    -- Common OKR fields (will be dynamically expanded based on CSV headers)
    department TEXT,
    objective TEXT,
    objective_type TEXT,
    priority TEXT,
    quarter TEXT,
    team_size INTEGER,
    budget NUMERIC(12,2),
    timeline_days INTEGER,
    progress NUMERIC(5,2),
    status TEXT,
    -- Validation fields
    valid BOOLEAN NOT NULL DEFAULT true,
    rejected_reason TEXT,
    processed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    -- Store original payload for reference
    original_payload JSONB
);

-- Indexes for okr_processed
CREATE INDEX IF NOT EXISTS idx_records_clean_source_file_id ON public.records_clean(source_file_id);
CREATE INDEX IF NOT EXISTS idx_records_clean_valid ON public.records_clean(valid);
CREATE INDEX IF NOT EXISTS idx_records_clean_processed_at ON public.records_clean(processed_at);
CREATE INDEX IF NOT EXISTS idx_records_clean_department ON public.records_clean(department);
CREATE INDEX IF NOT EXISTS idx_records_clean_status ON public.records_clean(status);
CREATE INDEX IF NOT EXISTS idx_records_clean_quarter ON public.records_clean(quarter);

-- Grant permissions on okr_processed
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO okr_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO okr_admin;

\c okr_curated;

-- Enable vector extension for embeddings support
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS public.documents (
    doc_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source TEXT NOT NULL, -- reference to source file/record
    text TEXT NOT NULL,
    meta JSONB NOT NULL,
    embedding vector(768) NULL, -- prepared for future embedding storage
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for okr_curated
CREATE INDEX IF NOT EXISTS idx_documents_source ON public.documents(source);
CREATE INDEX IF NOT EXISTS idx_documents_created_at ON public.documents(created_at);
CREATE INDEX IF NOT EXISTS idx_documents_meta_gin ON public.documents USING GIN(meta);
-- IVFFlat index for embeddings (will be created after embeddings are populated)
-- Uncommented but will create index only when embeddings exist
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_documents_embedding_ivfflat ON public.documents USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100) WHERE embedding IS NOT NULL;

-- Grant permissions on okr_curated
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO okr_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO okr_admin;

-- Return to default database
\c postgres;

-- Final message
SELECT 'OKR ETL databases and tables created successfully' AS status;

