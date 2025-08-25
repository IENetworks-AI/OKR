-- Database initialization script for OKR ETL pipeline
-- Creates three databases: okr_raw, okr_processed, okr_curated
-- Sets up tables, indexes, and extensions

-- Create databases
CREATE DATABASE okr_raw;
CREATE DATABASE okr_processed;
CREATE DATABASE okr_curated;

-- Create role for OKR operations
DO
$do$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'okr_admin') THEN
      CREATE ROLE okr_admin LOGIN PASSWORD 'okr_password';
   END IF;
END
$do$;

-- Grant privileges on databases
GRANT ALL PRIVILEGES ON DATABASE okr_raw TO okr_admin;
GRANT ALL PRIVILEGES ON DATABASE okr_processed TO okr_admin;
GRANT ALL PRIVILEGES ON DATABASE okr_curated TO okr_admin;

-- Connect to okr_raw database and create tables
\c okr_raw;

-- Create schema and tables for raw data
CREATE TABLE IF NOT EXISTS public.files (
    file_id SERIAL PRIMARY KEY,
    path VARCHAR(500) NOT NULL,
    sha256 VARCHAR(64) NOT NULL UNIQUE,
    rows INTEGER NOT NULL DEFAULT 0,
    ingested_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    file_size BIGINT,
    status VARCHAR(50) DEFAULT 'ingested'
);

CREATE TABLE IF NOT EXISTS public.records (
    record_id SERIAL PRIMARY KEY,
    file_id INTEGER NOT NULL REFERENCES public.files(file_id),
    row_num INTEGER NOT NULL,
    payload JSONB NOT NULL,
    loaded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(file_id, row_num)
);

-- Create indexes for raw data
CREATE INDEX IF NOT EXISTS idx_files_path ON public.files(path);
CREATE INDEX IF NOT EXISTS idx_files_ingested_at ON public.files(ingested_at);
CREATE INDEX IF NOT EXISTS idx_files_sha256 ON public.files(sha256);
CREATE INDEX IF NOT EXISTS idx_records_file_id ON public.records(file_id);
CREATE INDEX IF NOT EXISTS idx_records_loaded_at ON public.records(loaded_at);
CREATE INDEX IF NOT EXISTS idx_records_payload_gin ON public.records USING gin(payload);

-- Grant permissions on raw database objects
GRANT ALL ON ALL TABLES IN SCHEMA public TO okr_admin;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO okr_admin;

-- Connect to okr_processed database and create tables
\c okr_processed;

-- Create schema and tables for processed data
CREATE TABLE IF NOT EXISTS public.records_clean (
    record_id SERIAL PRIMARY KEY,
    source_file_id INTEGER NOT NULL,
    source_row_num INTEGER NOT NULL,
    -- Common OKR fields (will be dynamically extended based on CSV headers)
    department VARCHAR(100),
    objective TEXT,
    objective_type VARCHAR(50),
    priority VARCHAR(20),
    quarter VARCHAR(10),
    team_size INTEGER,
    budget DECIMAL(15,2),
    timeline_days INTEGER,
    progress DECIMAL(5,2),
    status VARCHAR(50),
    -- Data quality fields
    valid BOOLEAN NOT NULL DEFAULT true,
    rejected_reason TEXT,
    processed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    -- Store original data as backup
    original_data JSONB,
    UNIQUE(source_file_id, source_row_num)
);

-- Create indexes for processed data
CREATE INDEX IF NOT EXISTS idx_records_clean_source_file ON public.records_clean(source_file_id);
CREATE INDEX IF NOT EXISTS idx_records_clean_processed_at ON public.records_clean(processed_at);
CREATE INDEX IF NOT EXISTS idx_records_clean_valid ON public.records_clean(valid);
CREATE INDEX IF NOT EXISTS idx_records_clean_department ON public.records_clean(department);
CREATE INDEX IF NOT EXISTS idx_records_clean_status ON public.records_clean(status);
CREATE INDEX IF NOT EXISTS idx_records_clean_priority ON public.records_clean(priority);

-- Grant permissions on processed database objects
GRANT ALL ON ALL TABLES IN SCHEMA public TO okr_admin;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO okr_admin;

-- Connect to okr_curated database and create tables
\c okr_curated;

-- Enable pgvector extension for vector operations
CREATE EXTENSION IF NOT EXISTS vector;

-- Create schema and tables for curated data
CREATE TABLE IF NOT EXISTS public.documents (
    doc_id SERIAL PRIMARY KEY,
    source VARCHAR(100) NOT NULL, -- 'raw', 'processed', 'external'
    source_file_id INTEGER,
    source_row_num INTEGER,
    text TEXT NOT NULL,
    meta JSONB NOT NULL DEFAULT '{}',
    embedding vector(768) NULL, -- 768-dimensional embeddings (prepared for future use)
    chunk_index INTEGER DEFAULT 0, -- For chunked documents
    total_chunks INTEGER DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for curated data
CREATE INDEX IF NOT EXISTS idx_documents_source ON public.documents(source);
CREATE INDEX IF NOT EXISTS idx_documents_source_file ON public.documents(source_file_id);
CREATE INDEX IF NOT EXISTS idx_documents_created_at ON public.documents(created_at);
CREATE INDEX IF NOT EXISTS idx_documents_meta_gin ON public.documents USING gin(meta);
-- Commented out vector index until embeddings are populated
-- CREATE INDEX IF NOT EXISTS idx_documents_embedding ON public.documents USING ivfflat (embedding vector_cosine_ops);

-- Create trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_documents_updated_at 
    BEFORE UPDATE ON public.documents 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Grant permissions on curated database objects
GRANT ALL ON ALL TABLES IN SCHEMA public TO okr_admin;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO okr_admin;
GRANT ALL ON ALL FUNCTIONS IN SCHEMA public TO okr_admin;

-- Create a view for easy access to document metadata
CREATE VIEW public.document_summary AS
SELECT 
    doc_id,
    source,
    source_file_id,
    LENGTH(text) as text_length,
    chunk_index,
    total_chunks,
    meta->>'department' as department,
    meta->>'objective_type' as objective_type,
    meta->>'priority' as priority,
    created_at
FROM public.documents;

GRANT SELECT ON public.document_summary TO okr_admin;

-- Connect back to default postgres database
\c postgres;

-- Create a monitoring view that can be accessed from any database
CREATE OR REPLACE FUNCTION get_etl_stats()
RETURNS TABLE(
    database_name TEXT,
    table_name TEXT,
    record_count BIGINT,
    last_updated TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    -- This function would need to be called from each database individually
    -- or use dblink for cross-database queries (not implemented here for simplicity)
    RETURN QUERY SELECT 
        'monitoring'::TEXT as database_name,
        'placeholder'::TEXT as table_name,
        0::BIGINT as record_count,
        CURRENT_TIMESTAMP as last_updated;
END;
$$ LANGUAGE plpgsql;

GRANT EXECUTE ON FUNCTION get_etl_stats() TO okr_admin;