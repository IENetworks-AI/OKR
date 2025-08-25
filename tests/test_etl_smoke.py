"""
Smoke tests for ETL pipeline functionality
Tests basic ingestion, transformation, and loading without Airflow
"""

import pytest
import tempfile
import os
import json
import csv
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from data.preprocessing import (
    read_csv_to_json_rows, validate_and_clean, to_model_json, 
    chunk_text, calculate_file_hash
)
from data.streaming import publish_ingest_event, publish_processed_event
from utils.db import (
    test_connections, get_database_stats, insert_file_record,
    insert_raw_records, insert_processed_records, insert_curated_documents
)

class TestDataPreprocessing:
    """Test data preprocessing functions"""
    
    def test_csv_to_json_rows(self):
        """Test CSV reading and conversion to JSON rows"""
        # Create temporary CSV file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.writer(f)
            writer.writerow(['Department', 'Objective', 'Priority', 'Progress'])
            writer.writerow(['Engineering', 'Improve performance', 'High', '75'])
            writer.writerow(['Sales', 'Increase revenue', 'Medium', '60'])
            csv_path = f.name
        
        try:
            # Read CSV
            rows = list(read_csv_to_json_rows(csv_path))
            
            # Assertions
            assert len(rows) == 2
            assert rows[0]['department'] == 'Engineering'
            assert rows[0]['objective'] == 'Improve performance'
            assert rows[0]['priority'] == 'High'
            assert rows[0]['progress'] == 75  # Should be converted to int
            assert '_row_number' in rows[0]
            assert '_source_file' in rows[0]
            assert '_ingested_at' in rows[0]
            
        finally:
            os.unlink(csv_path)
    
    def test_validate_and_clean(self):
        """Test data validation and cleaning"""
        # Test valid row
        valid_row = {
            '_row_number': 1,
            '_source_file': 'test.csv',
            'department': 'Engineering',
            'progress': 75,
            'budget': '$10,000',
            'email': 'test@example.com'
        }
        
        cleaned_row, is_valid = validate_and_clean(valid_row)
        
        assert is_valid is True
        assert cleaned_row['department'] == 'Engineering'
        assert cleaned_row['progress'] == 75
        assert cleaned_row['budget'] == 10000.0  # Currency symbols removed
        assert '_validation_errors' in cleaned_row
        assert '_quality_score' in cleaned_row
        
        # Test invalid row
        invalid_row = {
            'department': 'Engineering',
            'progress': 150,  # Out of range
            'email': 'invalid-email'
        }
        
        cleaned_row, is_valid = validate_and_clean(invalid_row)
        
        assert is_valid is False
        assert len(cleaned_row['_validation_errors']) > 0
    
    def test_to_model_json(self):
        """Test conversion to model-ready JSON"""
        clean_row = {
            '_row_number': 1,
            '_source_file': 'test.csv',
            '_ingested_at': '2024-01-01T00:00:00',
            '_quality_score': 0.9,
            'department': 'Engineering',
            'objective': 'Improve system performance and reliability',
            'priority': 'High',
            'status': 'In Progress',
            'progress': 75
        }
        
        model_json = to_model_json(clean_row)
        
        assert 'text' in model_json
        assert 'meta' in model_json
        assert 'created_at' in model_json
        assert 'Improve system performance' in model_json['text']
        assert model_json['meta']['department'] == 'Engineering'
        assert model_json['meta']['priority'] == 'High'
        
        # Ensure JSON serializable
        json_str = json.dumps(model_json)
        assert json_str is not None
    
    def test_chunk_text(self):
        """Test text chunking functionality"""
        long_text = "This is a very long text that needs to be chunked. " * 100
        
        chunks = chunk_text(long_text, max_tokens=100, overlap=20)
        
        assert len(chunks) > 1
        assert all(isinstance(chunk, str) for chunk in chunks)
        assert all(len(chunk.split()) <= 100 for chunk in chunks)  # Rough token count
        
        # Test short text
        short_text = "Short text"
        short_chunks = chunk_text(short_text, max_tokens=100)
        assert len(short_chunks) == 1
        assert short_chunks[0] == short_text
    
    def test_file_hash_calculation(self):
        """Test file hash calculation"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content")
            temp_path = f.name
        
        try:
            hash1 = calculate_file_hash(temp_path)
            hash2 = calculate_file_hash(temp_path)
            
            assert hash1 == hash2  # Same file should have same hash
            assert len(hash1) == 64  # SHA256 hex length
            
        finally:
            os.unlink(temp_path)

class TestDatabaseOperations:
    """Test database operations (requires database connection)"""
    
    @pytest.mark.integration
    def test_database_connections(self):
        """Test connections to all ETL databases"""
        try:
            results = test_connections()
            
            # At least one database should be available for testing
            assert any(results.values()), "No database connections available for testing"
            
            # If any connection succeeds, test basic operations
            for db_name, connected in results.items():
                if connected:
                    print(f"✓ Successfully connected to {db_name}")
                else:
                    print(f"✗ Failed to connect to {db_name}")
                    
        except Exception as e:
            pytest.skip(f"Database connections not available: {e}")
    
    @pytest.mark.integration
    def test_database_stats(self):
        """Test database statistics retrieval"""
        try:
            stats = get_database_stats()
            assert isinstance(stats, dict)
            
            # Should have stats for all three databases
            expected_dbs = ['okr_raw', 'okr_processed', 'okr_curated']
            for db_name in expected_dbs:
                if db_name in stats and 'error' not in stats[db_name]:
                    print(f"✓ Retrieved stats for {db_name}: {stats[db_name]}")
                else:
                    print(f"✗ Could not retrieve stats for {db_name}")
                    
        except Exception as e:
            pytest.skip(f"Database stats not available: {e}")

class TestKafkaOperations:
    """Test Kafka operations (requires Kafka connection)"""
    
    @pytest.mark.integration
    def test_publish_ingest_event(self):
        """Test publishing ingestion event"""
        try:
            success = publish_ingest_event(
                file_path="test.csv",
                row_count=100,
                file_id=1
            )
            
            # If Kafka is available, should succeed
            # If not available, should fail gracefully
            print(f"Ingest event publish result: {success}")
            
        except Exception as e:
            pytest.skip(f"Kafka not available: {e}")
    
    @pytest.mark.integration
    def test_publish_processed_event(self):
        """Test publishing processed event"""
        try:
            success = publish_processed_event(
                processed_count=100,
                valid_count=90,
                invalid_count=10,
                batch_id="test_batch"
            )
            
            print(f"Processed event publish result: {success}")
            
        except Exception as e:
            pytest.skip(f"Kafka not available: {e}")

class TestEndToEndPipeline:
    """Test complete pipeline without Airflow"""
    
    def test_complete_etl_flow(self):
        """Test complete ETL flow with temporary data"""
        # Create sample CSV data
        sample_data = [
            ['Department', 'Objective', 'Priority', 'Progress', 'Budget'],
            ['Engineering', 'Improve system performance', 'High', '75', '$50000'],
            ['Sales', 'Increase quarterly revenue', 'Medium', '60', '$25000'],
            ['Marketing', 'Launch new campaign', 'High', '90', '$30000']
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.writer(f)
            writer.writerows(sample_data)
            csv_path = f.name
        
        try:
            # Step 1: Read CSV to JSON rows
            raw_rows = list(read_csv_to_json_rows(csv_path))
            assert len(raw_rows) == 3  # Header row excluded
            
            # Step 2: Validate and clean
            processed_records = []
            valid_count = 0
            invalid_count = 0
            
            for row in raw_rows:
                cleaned_row, is_valid = validate_and_clean(row)
                processed_records.append({
                    'source_file_id': 1,
                    'source_row_num': cleaned_row.get('_row_number'),
                    'valid': is_valid,
                    'original_data': row,
                    'department': cleaned_row.get('department'),
                    'progress': cleaned_row.get('progress'),
                    'budget': cleaned_row.get('budget')
                })
                
                if is_valid:
                    valid_count += 1
                else:
                    invalid_count += 1
            
            assert len(processed_records) == 3
            assert valid_count > 0  # At least some should be valid
            
            # Step 3: Convert to curated documents
            curated_documents = []
            
            for record in processed_records:
                if record['valid']:
                    model_json = to_model_json(record['original_data'])
                    
                    # Chunk if needed
                    text_content = model_json.get('text', '')
                    chunks = chunk_text(text_content, max_tokens=512, overlap=64)
                    
                    for i, chunk in enumerate(chunks):
                        document = {
                            'source': 'processed',
                            'source_file_id': record['source_file_id'],
                            'source_row_num': record['source_row_num'],
                            'text': chunk,
                            'meta': model_json.get('meta', {}),
                            'chunk_index': i,
                            'total_chunks': len(chunks)
                        }
                        curated_documents.append(document)
            
            assert len(curated_documents) > 0
            
            # Verify all documents are JSON serializable
            for doc in curated_documents:
                json_str = json.dumps(doc, default=str)
                assert json_str is not None
                
            print(f"✓ Complete ETL flow test passed:")
            print(f"  - Raw rows: {len(raw_rows)}")
            print(f"  - Processed records: {len(processed_records)} ({valid_count} valid, {invalid_count} invalid)")
            print(f"  - Curated documents: {len(curated_documents)}")
            
        finally:
            os.unlink(csv_path)

if __name__ == "__main__":
    # Run basic tests without pytest
    test_preprocessing = TestDataPreprocessing()
    test_preprocessing.test_csv_to_json_rows()
    test_preprocessing.test_validate_and_clean()
    test_preprocessing.test_to_model_json()
    test_preprocessing.test_chunk_text()
    test_preprocessing.test_file_hash_calculation()
    
    test_pipeline = TestEndToEndPipeline()
    test_pipeline.test_complete_etl_flow()
    
    print("✓ All smoke tests passed!")