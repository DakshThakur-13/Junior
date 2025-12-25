"""
Pytest configuration and shared fixtures for Junior test suite
"""
import sys
from pathlib import Path

# Add src to Python path so tests can import junior modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

# Optional: Add common fixtures here
import pytest


@pytest.fixture
def sample_case_data():
    """Sample case data for testing"""
    return {
        "id": 1,
        "title": "Test Case",
        "type": "Criminal",
        "status": "Active"
    }
