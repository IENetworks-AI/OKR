-- Create extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create role and database if not exists
DO $$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_catalog.pg_roles WHERE rolname = 'okr_admin'
   ) THEN
      CREATE ROLE okr_admin LOGIN PASSWORD 'okr_admin_password_change';
   END IF;
END
$$;

DO $$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_database WHERE datname = 'okr'
   ) THEN
      CREATE DATABASE okr OWNER okr_admin;
   END IF;
END
$$;

\connect okr;

-- Schemas
CREATE SCHEMA IF NOT EXISTS staging AUTHORIZATION okr_admin;
CREATE SCHEMA IF NOT EXISTS curated AUTHORIZATION okr_admin;
CREATE SCHEMA IF NOT EXISTS analytics AUTHORIZATION okr_admin;
CREATE SCHEMA IF NOT EXISTS registry AUTHORIZATION okr_admin;

-- Example vector table for RAG
CREATE TABLE IF NOT EXISTS curated.documents (
    id UUID PRIMARY KEY,
    source TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding vector(384) NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_documents_source ON curated.documents (source);
CREATE INDEX IF NOT EXISTS idx_documents_embedding ON curated.documents USING ivfflat (embedding vector_l2_ops) WITH (lists = 100);