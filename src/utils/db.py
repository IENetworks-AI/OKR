"""
Database utilities for OKR ETL pipeline
Provides PostgreSQL connection helpers and database operations
"""

import os
import logging
import json
from typing import Dict, Any, List, Optional, Literal, Union, Iterator
from contextlib import contextmanager
import psycopg2
import psycopg2.extras
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import pandas as pd
from io import StringIO

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Type for database names
DatabaseName = Literal["okr_raw", "okr_processed", "okr_curated"]

class DatabaseConfig:
    """Database configuration manager"""
    
    def __init__(self):
        self.host = os.getenv('POSTGRES_HOST', 'postgres')
        self.port = int(os.getenv('POSTGRES_PORT', '5432'))
        self.user = os.getenv('POSTGRES_USER', 'okr_admin')
        self.password = os.getenv('POSTGRES_PASSWORD', 'okr_password')
        self.default_db = os.getenv('POSTGRES_DB_DEFAULT', 'postgres')
        
    def get_connection_params(self, db_name: Optional[str] = None) -> Dict[str, Any]:
        """Get connection parameters for specified database"""
        return {
            'host': self.host,
            'port': self.port,
            'user': self.user,
            'password': self.password,
            'database': db_name or self.default_db
        }

# Global config instance
db_config = DatabaseConfig()

@contextmanager
def get_pg_conn(db_name: DatabaseName):
    """
    Get PostgreSQL connection context manager
    
    Args:
        db_name: Name of the database to connect to
        
    Yields:
        psycopg2.connection: Database connection
    """
    conn = None
    try:
        conn_params = db_config.get_connection_params(db_name)
        conn = psycopg2.connect(**conn_params)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        logger.debug(f"Connected to database: {db_name}")
        yield conn
    except Exception as e:
        logger.error(f"Error connecting to database {db_name}: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()
            logger.debug(f"Closed connection to database: {db_name}")

def execute_query(db_name: DatabaseName, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
    """
    Execute a SELECT query and return results as list of dictionaries
    
    Args:
        db_name: Database to query
        query: SQL query string
        params: Query parameters
        
    Returns:
        List of dictionaries representing query results
    """
    with get_pg_conn(db_name) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute(query, params)
            results = cursor.fetchall()
            return [dict(row) for row in results]

def execute_non_query(db_name: DatabaseName, query: str, params: Optional[tuple] = None) -> int:
    """
    Execute an INSERT/UPDATE/DELETE query
    
    Args:
        db_name: Database to execute against
        query: SQL query string
        params: Query parameters
        
    Returns:
        Number of affected rows
    """
    with get_pg_conn(db_name) as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            return cursor.rowcount

def bulk_insert(db_name: DatabaseName, table: str, data: List[Dict[str, Any]], 
                on_conflict: str = "DO NOTHING") -> int:
    """
    Perform bulk insert using executemany for better performance
    
    Args:
        db_name: Database to insert into
        table: Table name
        data: List of dictionaries to insert
        on_conflict: Conflict resolution strategy
        
    Returns:
        Number of inserted rows
    """
    if not data:
        return 0
        
    # Get column names from first record
    columns = list(data[0].keys())
    placeholders = ', '.join(['%s'] * len(columns))
    columns_str = ', '.join(columns)
    
    query = f"""
        INSERT INTO {table} ({columns_str}) 
        VALUES ({placeholders})
        ON CONFLICT {on_conflict}
    """
    
    # Convert data to tuples
    values = [tuple(row[col] for col in columns) for row in data]
    
    with get_pg_conn(db_name) as conn:
        with conn.cursor() as cursor:
            cursor.executemany(query, values)
            return cursor.rowcount

def copy_from_csv(db_name: DatabaseName, table: str, csv_data: str, 
                  columns: Optional[List[str]] = None) -> int:
    """
    Use PostgreSQL COPY command for high-performance CSV import
    
    Args:
        db_name: Database to import into
        table: Table name
        csv_data: CSV data as string
        columns: Column names (if None, assumes all columns)
        
    Returns:
        Number of imported rows
    """
    with get_pg_conn(db_name) as conn:
        with conn.cursor() as cursor:
            csv_buffer = StringIO(csv_data)
            
            if columns:
                columns_str = f"({', '.join(columns)})"
            else:
                columns_str = ""
                
            cursor.copy_expert(
                f"COPY {table} {columns_str} FROM STDIN WITH CSV HEADER",
                csv_buffer
            )
            return cursor.rowcount

def upsert_record(db_name: DatabaseName, table: str, data: Dict[str, Any], 
                  conflict_columns: List[str], update_columns: Optional[List[str]] = None) -> bool:
    """
    Insert or update a record using ON CONFLICT
    
    Args:
        db_name: Database to upsert into
        table: Table name
        data: Record data
        conflict_columns: Columns that define uniqueness
        update_columns: Columns to update on conflict (if None, updates all except conflict columns)
        
    Returns:
        True if record was inserted/updated successfully
    """
    columns = list(data.keys())
    placeholders = ', '.join(['%s'] * len(columns))
    columns_str = ', '.join(columns)
    conflict_str = ', '.join(conflict_columns)
    
    if update_columns is None:
        update_columns = [col for col in columns if col not in conflict_columns]
    
    update_str = ', '.join([f"{col} = EXCLUDED.{col}" for col in update_columns])
    
    query = f"""
        INSERT INTO {table} ({columns_str}) 
        VALUES ({placeholders})
        ON CONFLICT ({conflict_str}) 
        DO UPDATE SET {update_str}
    """
    
    values = tuple(data[col] for col in columns)
    
    try:
        with get_pg_conn(db_name) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, values)
                return True
    except Exception as e:
        logger.error(f"Error upserting record: {e}")
        return False

def get_file_record(file_path: str, sha256_hash: str) -> Optional[Dict[str, Any]]:
    """
    Get file record from raw database
    
    Args:
        file_path: Path to the file
        sha256_hash: SHA256 hash of the file
        
    Returns:
        File record if exists, None otherwise
    """
    query = "SELECT * FROM public.files WHERE path = %s OR sha256 = %s"
    results = execute_query("okr_raw", query, (file_path, sha256_hash))
    return results[0] if results else None

def insert_file_record(file_path: str, sha256_hash: str, row_count: int, 
                       file_size: Optional[int] = None) -> int:
    """
    Insert file record into raw database
    
    Args:
        file_path: Path to the file
        sha256_hash: SHA256 hash of the file
        row_count: Number of rows in the file
        file_size: Size of the file in bytes
        
    Returns:
        File ID of the inserted record
    """
    query = """
        INSERT INTO public.files (path, sha256, rows, file_size) 
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (sha256) DO UPDATE SET
            path = EXCLUDED.path,
            rows = EXCLUDED.rows,
            file_size = EXCLUDED.file_size,
            ingested_at = CURRENT_TIMESTAMP
        RETURNING file_id
    """
    
    with get_pg_conn("okr_raw") as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, (file_path, sha256_hash, row_count, file_size))
            return cursor.fetchone()[0]

def insert_raw_records(file_id: int, records: List[Dict[str, Any]]) -> int:
    """
    Insert raw records into raw database using COPY for performance
    
    Args:
        file_id: File ID from files table
        records: List of record dictionaries
        
    Returns:
        Number of inserted records
    """
    if not records:
        return 0
    
    # Prepare data for COPY
    csv_data = StringIO()
    csv_data.write("file_id,row_num,payload\n")
    
    for i, record in enumerate(records, 1):
        payload_json = json.dumps(record).replace('"', '""')  # Escape quotes for CSV
        csv_data.write(f'{file_id},{i},"{payload_json}"\n')
    
    csv_data.seek(0)
    csv_content = csv_data.getvalue()
    
    return copy_from_csv("okr_raw", "public.records", csv_content, 
                        ["file_id", "row_num", "payload"])

def get_raw_records_for_processing(limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Get raw records that need processing
    
    Args:
        limit: Maximum number of records to return
        
    Returns:
        List of raw records with metadata
    """
    query = """
        SELECT r.record_id, r.file_id, r.row_num, r.payload, r.loaded_at,
               f.path as file_path, f.sha256 as file_hash
        FROM public.records r
        JOIN public.files f ON r.file_id = f.file_id
        WHERE r.file_id NOT IN (
            SELECT DISTINCT source_file_id 
            FROM okr_processed.public.records_clean 
            WHERE source_file_id = r.file_id
        )
        ORDER BY r.loaded_at
    """
    
    if limit:
        query += f" LIMIT {limit}"
    
    return execute_query("okr_raw", query)

def insert_processed_records(records: List[Dict[str, Any]]) -> int:
    """
    Insert processed records into processed database
    
    Args:
        records: List of processed record dictionaries
        
    Returns:
        Number of inserted records
    """
    return bulk_insert("okr_processed", "public.records_clean", records,
                      "ON CONFLICT (source_file_id, source_row_num) DO UPDATE SET "
                      "processed_at = EXCLUDED.processed_at, "
                      "valid = EXCLUDED.valid, "
                      "rejected_reason = EXCLUDED.rejected_reason")

def insert_curated_documents(documents: List[Dict[str, Any]]) -> int:
    """
    Insert curated documents into curated database
    
    Args:
        documents: List of document dictionaries
        
    Returns:
        Number of inserted documents
    """
    return bulk_insert("okr_curated", "public.documents", documents,
                      "ON CONFLICT (source_file_id, source_row_num, chunk_index) DO UPDATE SET "
                      "text = EXCLUDED.text, "
                      "meta = EXCLUDED.meta, "
                      "updated_at = CURRENT_TIMESTAMP")

def get_database_stats() -> Dict[str, Dict[str, Any]]:
    """
    Get statistics for all ETL databases
    
    Returns:
        Dictionary with database statistics
    """
    stats = {}
    
    databases = ["okr_raw", "okr_processed", "okr_curated"]
    
    for db_name in databases:
        try:
            if db_name == "okr_raw":
                query = """
                    SELECT 
                        (SELECT COUNT(*) FROM public.files) as file_count,
                        (SELECT COUNT(*) FROM public.records) as record_count,
                        (SELECT MAX(ingested_at) FROM public.files) as last_ingestion
                """
            elif db_name == "okr_processed":
                query = """
                    SELECT 
                        (SELECT COUNT(*) FROM public.records_clean) as record_count,
                        (SELECT COUNT(*) FROM public.records_clean WHERE valid = true) as valid_count,
                        (SELECT COUNT(*) FROM public.records_clean WHERE valid = false) as invalid_count,
                        (SELECT MAX(processed_at) FROM public.records_clean) as last_processing
                """
            else:  # okr_curated
                query = """
                    SELECT 
                        (SELECT COUNT(*) FROM public.documents) as document_count,
                        (SELECT COUNT(DISTINCT source_file_id) FROM public.documents) as source_file_count,
                        (SELECT MAX(created_at) FROM public.documents) as last_creation
                """
            
            result = execute_query(db_name, query)
            stats[db_name] = result[0] if result else {}
            
        except Exception as e:
            logger.error(f"Error getting stats for {db_name}: {e}")
            stats[db_name] = {"error": str(e)}
    
    return stats

def test_connections() -> Dict[str, bool]:
    """
    Test connections to all ETL databases
    
    Returns:
        Dictionary with connection test results
    """
    results = {}
    
    for db_name in ["okr_raw", "okr_processed", "okr_curated"]:
        try:
            with get_pg_conn(db_name) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    results[db_name] = True
        except Exception as e:
            logger.error(f"Connection test failed for {db_name}: {e}")
            results[db_name] = False
    
    return results

if __name__ == "__main__":
    # Test database connections
    print("Testing database connections...")
    results = test_connections()
    for db_name, success in results.items():
        status = "✓" if success else "✗"
        print(f"{status} {db_name}: {'Connected' if success else 'Failed'}")
    
    # Print database statistics
    print("\nDatabase statistics:")
    stats = get_database_stats()
    for db_name, db_stats in stats.items():
        print(f"\n{db_name}:")
        for key, value in db_stats.items():
            print(f"  {key}: {value}")