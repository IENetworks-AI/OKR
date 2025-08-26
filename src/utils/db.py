
"""
Database Utilities Module

This module provides PostgreSQL connection helpers and utilities
for the OKR ETL pipeline.
"""

import os
import logging
import psycopg2
import psycopg2.extras
from psycopg2 import sql
from typing import Literal, Dict, Any, List, Optional, Iterator
from contextlib import contextmanager
import json
from datetime import datetime
import io
import csv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Database name type
DBName = Literal["okr_raw", "okr_processed", "okr_curated"]


def get_pg_conn(db_name: DBName) -> psycopg2.extensions.connection:
    """
    Get PostgreSQL connection for specified database.
    
    Args:
        db_name: Database name (okr_raw, okr_processed, or okr_curated)
        
    Returns:
        psycopg2 connection object
    """
    # Get connection parameters from environment
    host = os.getenv('POSTGRES_HOST', 'postgres')
    port = os.getenv('POSTGRES_PORT', '5432')
    user = os.getenv('POSTGRES_USER', 'okr_admin')
    password = os.getenv('POSTGRES_PASSWORD', 'okr_password')
    
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=db_name,
            user=user,
            password=password,
            options='-c statement_timeout=30000'  # 30 second timeout
        )
        conn.set_session(autocommit=False)
        logger.info(f"Connected to PostgreSQL database: {db_name}")
        return conn
    except Exception as e:
        logger.error(f"Error connecting to database {db_name}: {e}")
        raise


@contextmanager
def get_db_connection(db_name: DBName):
    """
    Context manager for database connections with automatic cleanup.
    
    Args:
        db_name: Database name
        
    Yields:
        psycopg2 connection object
    """
    conn = None
    try:
        conn = get_pg_conn(db_name)
        yield conn
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Database operation failed: {e}")
        raise
    finally:
        if conn:
            conn.close()


def upsert_file_metadata(conn: psycopg2.extensions.connection, path: str, sha256: str, rows: int) -> str:
    """
    Upsert file metadata into okr_raw.files table.
    
    Args:
        conn: Database connection
        path: File path
        sha256: File SHA256 hash
        rows: Number of rows in file
        
    Returns:
        str: File ID (UUID)
    """
    try:
        with conn.cursor() as cur:
            # Use ON CONFLICT to handle duplicates
            cur.execute("""
                INSERT INTO public.files (path, sha256, rows, ingested_at)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (path, sha256) DO UPDATE SET
                    rows = EXCLUDED.rows,
                    ingested_at = EXCLUDED.ingested_at
                RETURNING file_id
            """, (path, sha256, rows, datetime.now()))
            
            file_id = cur.fetchone()[0]
            conn.commit()
            logger.info(f"File metadata upserted: {path} -> {file_id}")
            return str(file_id)
            
    except Exception as e:
        conn.rollback()
        logger.error(f"Error upserting file metadata: {e}")
        raise


def copy_json_records_to_raw(conn: psycopg2.extensions.connection, file_id: str, records: List[Dict[str, Any]]) -> int:
    """
    Efficiently copy JSON records to okr_raw.records using COPY.
    
    Args:
        conn: Database connection
        file_id: File ID from files table
        records: List of record dictionaries
        
    Returns:
        int: Number of records inserted
    """
    try:
        # Prepare data for COPY
        csv_data = io.StringIO()
        writer = csv.writer(csv_data, delimiter='\t')
        
        for i, record in enumerate(records, 1):
            # Remove metadata fields before storing
            payload = {k: v for k, v in record.items() if not k.startswith('_')}
            row_data = [
                file_id,  # file_id
                record.get('_row_num', i),  # row_num
                json.dumps(payload, default=str),  # payload as JSON
                datetime.now().isoformat()  # loaded_at
            ]
            writer.writerow(row_data)
        
        # Use COPY for efficient bulk insert
        csv_data.seek(0)
        with conn.cursor() as cur:
            cur.copy_from(
                csv_data,
                'public.records',
                columns=('file_id', 'row_num', 'payload', 'loaded_at'),
                sep='\t'
            )
            
        conn.commit()
        count = len(records)
        logger.info(f"Copied {count} records to okr_raw.records")
        return count
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error copying records to raw: {e}")
        raise


def insert_processed_records(conn: psycopg2.extensions.connection, records: List[Dict[str, Any]]) -> int:
    """
    Insert processed records into okr_processed.records_clean.
    
    Args:
        conn: Database connection to okr_processed
        records: List of processed record dictionaries
        
    Returns:
        int: Number of records inserted
    """
    try:
        with conn.cursor() as cur:
            # Prepare insert statement
            insert_sql = """
                INSERT INTO public.records_clean (
                    source_file_id, source_row_num, department, objective, objective_type,
                    priority, quarter, team_size, budget, timeline_days, progress, status,
                    valid, rejected_reason, original_payload, processed_at
                ) VALUES %s
            """
            
            # Prepare data tuples
            data_tuples = []
            for record in records:
                data_tuple = (
                    record.get('_source_file_id'),
                    record.get('_row_num'),
                    record.get('department'),
                    record.get('objective'),
                    record.get('objective_type'),
                    record.get('priority'),
                    record.get('quarter'),
                    record.get('team_size'),
                    record.get('budget'),
                    record.get('timeline_days'),
                    record.get('progress'),
                    record.get('status'),
                    record.get('_is_valid', True),
                    '; '.join(record.get('_validation_errors', [])) if record.get('_validation_errors') else None,
                    json.dumps({k: v for k, v in record.items() if not k.startswith('_')}, default=str),
                    datetime.now()
                )
                data_tuples.append(data_tuple)
            
            # Execute batch insert
            psycopg2.extras.execute_values(cur, insert_sql, data_tuples)
            
        conn.commit()
        count = len(records)
        logger.info(f"Inserted {count} records into okr_processed.records_clean")
        return count
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error inserting processed records: {e}")
        raise


def insert_curated_documents(conn: psycopg2.extensions.connection, documents: List[Dict[str, Any]]) -> int:
    """
    Insert curated documents into okr_curated.documents.
    
    Args:
        conn: Database connection to okr_curated
        documents: List of document dictionaries with text and meta
        
    Returns:
        int: Number of documents inserted
    """
    try:
        with conn.cursor() as cur:
            # Prepare insert statement
            insert_sql = """
                INSERT INTO public.documents (source, text, meta, created_at)
                VALUES %s
            """
            
            # Prepare data tuples
            data_tuples = []
            for doc in documents:
                # Create source identifier
                meta = doc.get('meta', {})
                source = f"{meta.get('source_file', 'unknown')}#{meta.get('row_num', 0)}"
                
                data_tuple = (
                    source,
                    doc.get('text', ''),
                    json.dumps(doc.get('meta', {}), default=str),
                    datetime.now()
                )
                data_tuples.append(data_tuple)
            
            # Execute batch insert
            psycopg2.extras.execute_values(cur, insert_sql, data_tuples)
            
        conn.commit()
        count = len(documents)
        logger.info(f"Inserted {count} documents into okr_curated.documents")
        return count
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error inserting curated documents: {e}")
        raise


def get_unprocessed_files(conn: psycopg2.extensions.connection) -> List[Dict[str, Any]]:
    """
    Get list of files that haven't been processed yet.
    
    Args:
        conn: Database connection to okr_raw
        
    Returns:
        List of file metadata dictionaries
    """
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT file_id, path, sha256, rows, ingested_at
                FROM public.files
                ORDER BY ingested_at DESC
            """)
            
            files = [dict(row) for row in cur.fetchall()]
            logger.info(f"Found {len(files)} files in okr_raw.files")
            return files
            
    except Exception as e:
        logger.error(f"Error getting unprocessed files: {e}")
        raise


def get_raw_records(conn: psycopg2.extensions.connection, file_id: str) -> Iterator[Dict[str, Any]]:
    """
    Get raw records for a specific file.
    
    Args:
        conn: Database connection to okr_raw
        file_id: File ID to get records for
        
    Yields:
        Dict containing record data
    """
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT record_id, file_id, row_num, payload, loaded_at
                FROM public.records
                WHERE file_id = %s
                ORDER BY row_num
            """, (file_id,))
            
            for row in cur:
                # Parse JSON payload and add metadata
                record = dict(row['payload'])
                record['_record_id'] = str(row['record_id'])
                record['_file_id'] = str(row['file_id'])
                record['_row_num'] = row['row_num']
                record['_loaded_at'] = row['loaded_at'].isoformat()
                yield record
                
    except Exception as e:
        logger.error(f"Error getting raw records for file {file_id}: {e}")
        raise


def test_connections() -> Dict[str, bool]:
    """
    Test connections to all three databases.
    
    Returns:
        Dict mapping database names to connection success status
    """
    results = {}
    
    for db_name in ["okr_raw", "okr_processed", "okr_curated"]:
        try:
            with get_db_connection(db_name) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    cur.fetchone()
                results[db_name] = True
                logger.info(f"Connection test successful for {db_name}")
        except Exception as e:
            results[db_name] = False
            logger.error(f"Connection test failed for {db_name}: {e}")
    
    return results


def get_database_stats() -> Dict[str, Dict[str, int]]:
    """
    Get statistics for all databases.
    
    Returns:
        Dict with database stats
    """
    stats = {}
    
    # okr_raw stats
    try:
        with get_db_connection("okr_raw") as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM public.files")
                file_count = cur.fetchone()[0]
                
                cur.execute("SELECT COUNT(*) FROM public.records")
                record_count = cur.fetchone()[0]
                
                stats["okr_raw"] = {
                    "files": file_count,
                    "records": record_count
                }
    except Exception as e:
        logger.error(f"Error getting okr_raw stats: {e}")
        stats["okr_raw"] = {"error": str(e)}
    
    # okr_processed stats
    try:
        with get_db_connection("okr_processed") as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM public.records_clean")
                clean_count = cur.fetchone()[0]
                
                cur.execute("SELECT COUNT(*) FROM public.records_clean WHERE valid = true")
                valid_count = cur.fetchone()[0]
                
                stats["okr_processed"] = {
                    "total_records": clean_count,
                    "valid_records": valid_count,
                    "invalid_records": clean_count - valid_count
                }
    except Exception as e:
        logger.error(f"Error getting okr_processed stats: {e}")
        stats["okr_processed"] = {"error": str(e)}
    
    # okr_curated stats
    try:
        with get_db_connection("okr_curated") as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM public.documents")
                doc_count = cur.fetchone()[0]
                
                cur.execute("SELECT COUNT(*) FROM public.documents WHERE embedding IS NOT NULL")
                embedded_count = cur.fetchone()[0]
                
                stats["okr_curated"] = {
                    "documents": doc_count,
                    "with_embeddings": embedded_count
                }
    except Exception as e:
        logger.error(f"Error getting okr_curated stats: {e}")
        stats["okr_curated"] = {"error": str(e)}
    
    return stats
