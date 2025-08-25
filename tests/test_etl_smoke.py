"""
ETL Pipeline Smoke Tests

This module contains pytest tests to verify the ETL pipeline functionality
without requiring Airflow. Tests create temporary CSV files and run the
ingestion/transform functions directly.
"""

import pytest
import os
import sys
import tempfile
import json
import csv
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from data.preprocessing import (
    read_csv_to_json_rows, validate_and_clean, to_model_json, chunk_text
)
from data.streaming import publish_ingest_event, publish_processed_event
from utils.db import get_database_stats, test_connections


class TestPreprocessingFunctions:
    """Test the pure preprocessing functions"""
    
    def test_read_csv_to_json_rows(self):
        """Test CSV reading functionality"""
        # Create temporary CSV file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.writer(f)
            writer.writerow(['department', 'objective', 'priority', 'progress'])
            writer.writerow(['Engineering', 'Improve code quality', 'High', '75.5'])
            writer.writerow(['Sales', 'Increase revenue', 'Medium', '60.0'])
            temp_file = f.name
        
        try:
            # Test reading
            rows = list(read_csv_to_json_rows(temp_file))
            
            assert len(rows) == 2
            assert rows[0]['department'] == 'Engineering'
            assert rows[0]['objective'] == 'Improve code quality'
            assert rows[0]['priority'] == 'High'
            assert rows[0]['progress'] == '75.5'
            assert rows[0]['_row_num'] == 1
            assert rows[0]['_source_file'] == temp_file
            
            assert rows[1]['department'] == 'Sales'
            assert rows[1]['_row_num'] == 2
            
        finally:
            os.unlink(temp_file)
    
    def test_validate_and_clean(self):
        """Test data validation and cleaning"""
        # Test valid record
        valid_record = {
            'department': 'Engineering',
            'objective': 'Improve code quality',
            'priority': 'high',
            'progress': '75.5',
            'team_size': '5',
            '_row_num': 1,
            '_source_file': 'test.csv'
        }
        
        cleaned, is_valid = validate_and_clean(valid_record)
        
        assert is_valid
        assert cleaned['department'] == 'Engineering'
        assert cleaned['priority'] == 'High'  # Should be title cased
        assert cleaned['progress'] == 75.5  # Should be converted to float
        assert cleaned['team_size'] == 5  # Should be converted to int
        assert cleaned['_is_valid'] == True
        
        # Test invalid record (empty objective)
        invalid_record = {
            'department': 'Sales',
            'objective': '',
            'priority': 'medium',
            '_row_num': 2,
            '_source_file': 'test.csv'
        }
        
        cleaned, is_valid = validate_and_clean(invalid_record)
        
        assert not is_valid
        assert cleaned['_is_valid'] == False
        assert len(cleaned['_validation_errors']) > 0
    
    def test_to_model_json(self):
        """Test conversion to model JSON format"""
        record = {
            'department': 'Engineering',
            'objective': 'Improve code quality',
            'priority': 'High',
            'progress': 75.5,
            'team_size': 5,
            'status': 'On Track',
            '_row_num': 1,
            '_source_file': 'test.csv',
            '_is_valid': True
        }
        
        model_json = to_model_json(record)
        
        # Check structure
        assert 'text' in model_json
        assert 'meta' in model_json
        assert 'labels' in model_json
        
        # Check text content
        text = model_json['text']
        assert 'Objective: Improve code quality' in text
        assert 'Department: Engineering' in text
        assert 'Progress: 75.5%' in text
        
        # Check labels
        labels = model_json['labels']
        assert labels['department'] == 'Engineering'
        assert labels['priority'] == 'High'
        assert labels['status'] == 'On Track'
        
        # Check metadata
        meta = model_json['meta']
        assert meta['source_file'] == 'test.csv'
        assert meta['row_num'] == 1
        assert meta['is_valid'] == True
        
        # Ensure JSON serializable
        json_str = json.dumps(model_json)
        assert isinstance(json_str, str)
    
    def test_chunk_text(self):
        """Test text chunking functionality"""
        # Short text - should not be chunked
        short_text = "This is a short objective."
        chunks = chunk_text(short_text, max_tokens=50)
        assert len(chunks) == 1
        assert chunks[0] == short_text
        
        # Long text - should be chunked
        long_text = " ".join(["This is a very long objective that should be chunked."] * 20)
        chunks = chunk_text(long_text, max_tokens=50, overlap=10)
        assert len(chunks) > 1
        
        # All chunks should be non-empty strings
        for chunk in chunks:
            assert isinstance(chunk, str)
            assert len(chunk.strip()) > 0


class TestStreamingFunctions:
    """Test streaming functionality (mocked)"""
    
    @patch('data.streaming.get_producer')
    def test_publish_ingest_event(self, mock_get_producer):
        """Test publishing ingest events"""
        # Mock Kafka producer
        mock_producer = MagicMock()
        mock_future = MagicMock()
        mock_metadata = MagicMock()
        mock_metadata.partition = 0
        mock_metadata.offset = 123
        mock_future.get.return_value = mock_metadata
        mock_producer.send.return_value = mock_future
        mock_get_producer.return_value = mock_producer
        
        # Test publishing
        result = publish_ingest_event('test.csv', 100)
        
        assert result == True
        mock_producer.send.assert_called_once()
        mock_producer.close.assert_called_once()
        
        # Check the message structure
        call_args = mock_producer.send.call_args
        assert call_args[1]['topic'] == 'okr_raw_ingest'
        assert call_args[1]['key'] == 'test.csv'
        
        message = call_args[1]['value']
        assert message['event_type'] == 'raw_ingest'
        assert message['file_path'] == 'test.csv'
        assert message['rows_ingested'] == 100
        assert message['status'] == 'completed'
    
    @patch('data.streaming.get_producer')
    def test_publish_processed_event(self, mock_get_producer):
        """Test publishing processed events"""
        # Mock Kafka producer
        mock_producer = MagicMock()
        mock_future = MagicMock()
        mock_metadata = MagicMock()
        mock_metadata.partition = 0
        mock_metadata.offset = 124
        mock_future.get.return_value = mock_metadata
        mock_producer.send.return_value = mock_future
        mock_get_producer.return_value = mock_producer
        
        # Test publishing
        result = publish_processed_event(50)
        
        assert result == True
        mock_producer.send.assert_called_once()
        mock_producer.close.assert_called_once()
        
        # Check the message structure
        call_args = mock_producer.send.call_args
        assert call_args[1]['topic'] == 'okr_processed_updates'
        
        message = call_args[1]['value']
        assert message['event_type'] == 'processed_update'
        assert message['records_processed'] == 50
        assert message['status'] == 'completed'


class TestDatabaseOperations:
    """Test database operations (requires running database)"""
    
    @pytest.mark.integration
    def test_database_connections(self):
        """Test connections to all three databases"""
        # This test requires the databases to be running
        # Skip if not available
        try:
            results = test_connections()
            
            # At least check that the function returns the expected structure
            assert isinstance(results, dict)
            assert 'okr_raw' in results
            assert 'okr_processed' in results
            assert 'okr_curated' in results
            
        except Exception as e:
            pytest.skip(f"Database not available: {e}")
    
    @pytest.mark.integration
    def test_database_stats(self):
        """Test getting database statistics"""
        # This test requires the databases to be running
        try:
            stats = get_database_stats()
            
            # Check structure
            assert isinstance(stats, dict)
            
            # Check that we get stats for each database
            for db_name in ['okr_raw', 'okr_processed', 'okr_curated']:
                assert db_name in stats
                db_stats = stats[db_name]
                
                # Either we get valid stats or an error
                if 'error' not in db_stats:
                    # Should have numeric values
                    for key, value in db_stats.items():
                        assert isinstance(value, int)
                        assert value >= 0
                        
        except Exception as e:
            pytest.skip(f"Database not available: {e}")


class TestEndToEndPipeline:
    """End-to-end pipeline test"""
    
    def test_complete_pipeline_flow(self):
        """Test the complete pipeline flow without database/Kafka"""
        # Create test CSV data
        test_data = [
            ['department', 'objective', 'priority', 'progress', 'team_size'],
            ['Engineering', 'Improve code quality', 'High', '75.5', '5'],
            ['Sales', 'Increase revenue', 'Medium', '60.0', '3'],
            ['Marketing', 'Brand awareness', 'Low', '30.0', '2'],
            ['HR', '', 'High', '90.0', '1']  # Invalid - empty objective
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.writer(f)
            writer.writerows(test_data)
            temp_file = f.name
        
        try:
            # Step 1: Read CSV
            raw_records = list(read_csv_to_json_rows(temp_file))
            assert len(raw_records) == 4  # 4 data rows
            
            # Step 2: Validate and clean
            processed_records = []
            valid_count = 0
            for record in raw_records:
                cleaned, is_valid = validate_and_clean(record)
                processed_records.append(cleaned)
                if is_valid:
                    valid_count += 1
            
            assert len(processed_records) == 4
            assert valid_count == 3  # HR record should be invalid
            
            # Step 3: Convert to model JSON
            model_documents = []
            for record in processed_records:
                if record.get('_is_valid', False):
                    model_json = to_model_json(record)
                    model_documents.append(model_json)
            
            assert len(model_documents) == 3  # Only valid records
            
            # Step 4: Test JSON serialization
            for doc in model_documents:
                json_str = json.dumps(doc, default=str)
                assert isinstance(json_str, str)
                
                # Parse back to ensure valid JSON
                parsed = json.loads(json_str)
                assert 'text' in parsed
                assert 'meta' in parsed
            
            # Step 5: Test chunking on a long text
            long_objective = "This is a very long objective " * 50
            long_record = {
                'objective': long_objective,
                'department': 'Test',
                '_row_num': 1,
                '_source_file': 'test.csv',
                '_is_valid': True
            }
            
            model_json = to_model_json(long_record)
            chunks = chunk_text(model_json['text'], max_tokens=100)
            assert len(chunks) > 1
            
        finally:
            os.unlink(temp_file)


def test_import_all_modules():
    """Test that all required modules can be imported"""
    # Test imports
    from data.preprocessing import read_csv_to_json_rows, validate_and_clean, to_model_json, chunk_text
    from data.streaming import publish_ingest_event, publish_processed_event
    from utils.db import get_database_stats, test_connections
    
    # All functions should be callable
    assert callable(read_csv_to_json_rows)
    assert callable(validate_and_clean)
    assert callable(to_model_json)
    assert callable(chunk_text)
    assert callable(publish_ingest_event)
    assert callable(publish_processed_event)
    assert callable(get_database_stats)
    assert callable(test_connections)


if __name__ == "__main__":
    # Run basic tests
    pytest.main([__file__, "-v"])
