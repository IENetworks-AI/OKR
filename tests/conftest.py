"""
Pytest configuration and fixtures
"""
import pytest
import os
import sys
from pathlib import Path

# Add project paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

@pytest.fixture(scope="session")
def project_root_path():
    """Fixture providing project root path"""
    return project_root

@pytest.fixture(scope="session")
def test_data_dir(tmp_path_factory):
    """Create temporary test data directory"""
    return tmp_path_factory.mktemp("test_data")