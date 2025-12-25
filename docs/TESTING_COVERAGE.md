# Test Coverage Documentation

## Overview

Junior now has comprehensive test coverage tracking configured using pytest and pytest-cov.

## Configuration Files

- **`pytest.ini`** - Main pytest configuration with coverage settings
- **`.coveragerc`** - Coverage.py configuration for report generation
- **`tests/conftest.py`** - Shared test fixtures and setup

## Running Tests with Coverage

### Quick Run (All Tests)
```powershell
# PowerShell
.\run_tests_coverage.ps1

# Or manually
python -m pytest
```

### Specific Test File
```powershell
python -m pytest tests/test_example.py -v
```

### With Coverage Report
```powershell
python -m pytest --cov=src/junior --cov-report=html --cov-report=term
```

### Skip Slow Tests
```powershell
python -m pytest -m "not slow"
```

## Coverage Reports

After running tests with coverage, reports are generated in multiple formats:

### HTML Report
- Location: `htmlcov/index.html`
- Open in browser to see detailed line-by-line coverage
- Shows which lines were executed during tests

### Terminal Report
- Shows summary with missing lines
- Displayed immediately after test run

### XML Report
- Location: `coverage.xml`
- Used by CI/CD tools and coverage services

## Test Markers

Tests can be categorized using pytest markers:

```python
@pytest.mark.unit
def test_fast_function():
    """Quick unit test"""
    pass

@pytest.mark.integration
def test_api_endpoint():
    """Integration test requiring services"""
    pass

@pytest.mark.slow
def test_full_pipeline():
    """Slow end-to-end test"""
    pass
```

Run specific categories:
```powershell
pytest -m unit        # Only unit tests
pytest -m integration # Only integration tests
pytest -m "not slow"  # Skip slow tests
```

## Coverage Targets

Current coverage threshold: **30%** (configurable in pytest.ini)

### Coverage by Component

| Component | Target | Priority |
|-----------|--------|----------|
| API Endpoints | 80% | High |
| Core Services | 70% | High |
| Agents | 60% | Medium |
| Utilities | 50% | Medium |

## Writing Tests

### Example Test Structure

```python
# tests/test_myfeature.py
import pytest
from junior.services.myservice import MyService


@pytest.mark.unit
def test_basic_functionality():
    """Test basic function works"""
    service = MyService()
    result = service.process("test")
    assert result is not None


@pytest.mark.asyncio
async def test_async_function():
    """Test async operations"""
    service = MyService()
    result = await service.async_process("test")
    assert result.success


def test_with_fixture(sample_case_data):
    """Test using shared fixture"""
    assert sample_case_data["id"] == 1
```

## CI/CD Integration

The coverage reports (especially `coverage.xml`) can be integrated with:
- **GitHub Actions** - Automated testing on push/PR
- **Codecov** - Coverage tracking over time
- **SonarQube** - Code quality analysis

## Improving Coverage

To improve test coverage:

1. **Identify gaps**: Check `htmlcov/index.html` for uncovered lines
2. **Write targeted tests**: Focus on high-priority components
3. **Mock external services**: Use pytest fixtures for API dependencies
4. **Test edge cases**: Cover error paths and boundary conditions

## Excluding Code from Coverage

Use pragma comments for code that shouldn't be measured:

```python
if __name__ == "__main__":  # pragma: no cover
    main()

def debug_only():  # pragma: no cover
    """Development-only function"""
    pass
```

## Dependencies

Required packages (already in requirements.txt):
- `pytest>=8.0.0` - Test framework
- `pytest-cov>=4.1.0` - Coverage plugin
- `pytest-asyncio>=0.23.0` - Async test support

## Troubleshooting

### Import Errors
Make sure virtual environment is activated and dependencies installed:
```powershell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Coverage Not Showing
Check that tests are in `tests/` directory and follow naming convention `test_*.py`.

### Slow Tests
Mark slow tests and skip them during development:
```python
@pytest.mark.slow
def test_expensive_operation():
    pass
```

Then run: `pytest -m "not slow"`
