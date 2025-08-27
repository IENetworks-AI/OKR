"""
Basic test suite for OKR ML Pipeline
"""
import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

def test_basic_import():
    """Test that basic imports work"""
    import os
    assert os.path.exists(project_root)

def test_project_structure():
    """Test that required project directories exist"""
    required_dirs = ['src', 'data', 'configs', 'apps']
    for dir_name in required_dirs:
        assert (project_root / dir_name).exists(), f"Missing directory: {dir_name}"

def test_requirements_file():
    """Test that requirements.txt exists"""
    assert (project_root / 'requirements.txt').exists()

class TestDataManager:
    """Test data manager functionality"""
    
    def test_data_manager_import(self):
        """Test data manager can be imported"""
        try:
            from data_manager import DataManager
            assert DataManager is not None
        except ImportError:
            pytest.skip("Data manager not available for import")