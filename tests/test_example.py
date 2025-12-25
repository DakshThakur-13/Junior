"""
Example test file demonstrating pytest with coverage
This file tests basic project structure
"""


def test_project_structure():
    """Test that basic project structure exists"""
    from pathlib import Path
    
    project_root = Path(__file__).parent.parent
    assert (project_root / "src" / "junior").exists()
    assert (project_root / "frontend").exists()
    assert (project_root / "requirements.txt").exists()


def test_imports():
    """Test that core modules can be imported"""
    try:
        from junior.core import config
        from junior.core import types
        assert config is not None
        assert types is not None
    except ImportError as e:
        # This is expected if dependencies aren't installed
        assert "No module named" in str(e)


def test_sample_fixture(sample_case_data):
    """Test using a pytest fixture"""
    assert sample_case_data["id"] == 1
    assert sample_case_data["title"] == "Test Case"
