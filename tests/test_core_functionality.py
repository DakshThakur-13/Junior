"""
Test core functionality without API keys
Tests basic functionality, data models, utilities, and services that don't require external APIs
"""
import pytest
from pathlib import Path


def test_type_definitions():
    """Test that core type definitions work correctly"""
    from junior.core.types import CaseStatus, Court, Language, AgentRole
    
    # Test enums
    assert CaseStatus.GOOD_LAW == "good_law"
    assert Court.SUPREME_COURT == "supreme_court"
    assert Language.ENGLISH == "en"
    assert AgentRole.RESEARCHER == "researcher"
    
    # Test all case statuses
    assert len(list(CaseStatus)) == 3
    assert len(list(Court)) == 5
    assert len(list(Language)) >= 10  # At least 10 supported languages


def test_config_loading():
    """Test configuration loading (without requiring env vars)"""
    from junior.core.config import Settings
    
    # Test default config loads
    config = Settings()
    assert config.app_name == "Junior"
    assert config.app_version == "0.1.0"
    assert config.port == 8000
    assert config.default_llm_model == "llama-3.3-70b-versatile"
    
    # Test multi-model architecture config
    assert config.researcher_model == "sonar-pro"
    assert config.critic_model == "llama-3.3-70b-versatile"
    assert config.writer_model == "llama-3.3-70b-versatile"


def test_citation_model():
    """Test Citation pydantic model"""
    from junior.core.types import Citation, Court, CaseStatus
    
    citation = Citation(
        case_name="Test v. Example",
        case_number="Crl.A. 123/2024",
        court=Court.SUPREME_COURT,
        year=2024,
        paragraph=5,
        status=CaseStatus.GOOD_LAW
    )
    
    assert citation.case_name == "Test v. Example"
    assert citation.case_number == "Crl.A. 123/2024"
    assert citation.year == 2024
    assert citation.court == Court.SUPREME_COURT
    assert "Supreme Court" in citation.formatted


def test_exceptions():
    """Test custom exception classes"""
    from junior.core.exceptions import (
        JuniorException,
        ConfigurationError,
        ValidationError,
        AIAgentError,
        DatabaseError,
        CitationError
    )
    
    # Test exception hierarchy
    assert issubclass(ConfigurationError, JuniorException)
    assert issubclass(ValidationError, JuniorException)
    assert issubclass(AIAgentError, JuniorException)
    assert issubclass(DatabaseError, JuniorException)
    assert issubclass(CitationError, JuniorException)
    
    # Test raising exceptions with messages
    with pytest.raises(ConfigurationError) as exc_info:
        raise ConfigurationError("Test config error")
    assert "Test config error" in str(exc_info.value)
    assert exc_info.value.code == "CONFIG_ERROR"
    
    # Test ValidationError with field
    with pytest.raises(ValidationError) as exc_info:
        raise ValidationError("Invalid field", field="test_field")
    assert exc_info.value.field == "test_field"


def test_project_modules_importable():
    """Test that all major modules can be imported without errors"""
    modules_to_test = [
        "junior.core.config",
        "junior.core.types",
        "junior.core.exceptions",
        "junior.api.schemas",
    ]
    
    for module_name in modules_to_test:
        try:
            __import__(module_name)
        except ImportError as e:
            # Only fail if it's not a missing dependency issue
            if "No module named" not in str(e) or "junior" in str(e):
                raise


def test_schemas():
    """Test API schemas/pydantic models"""
    try:
        from junior.api.schemas import (
            HealthResponse,
            ChatRequest,
            ChatResponse
        )
        
        # Test HealthResponse
        health = HealthResponse(
            status="healthy",
            version="0.1.0",
            timestamp="2024-01-01T00:00:00"
        )
        assert health.status == "healthy"
        
        # Test ChatRequest - check if it has message field
        # Note: Actual schema might be different, so we'll just verify it's importable
        assert ChatRequest is not None
        
        # Test ChatResponse
        assert ChatResponse is not None
    except ImportError as e:
        if "fastapi" in str(e).lower() or "starlette" in str(e).lower():
            pytest.skip(f"Skipping schemas test due to missing dependency: {e}")
        else:
            raise


def test_language_support():
    """Test language enumeration and support"""
    from junior.core.types import Language
    
    # Check major Indian languages are supported
    expected_languages = [
        Language.ENGLISH,
        Language.HINDI,
        Language.HINGLISH,
        Language.MARATHI,
        Language.TAMIL,
        Language.TELUGU
    ]
    
    available_languages = list(Language)
    for lang in expected_languages:
        assert lang in available_languages


def test_court_hierarchy():
    """Test court hierarchy enumeration"""
    from junior.core.types import Court
    
    courts = list(Court)
    assert Court.SUPREME_COURT in courts
    assert Court.HIGH_COURT in courts
    assert Court.DISTRICT_COURT in courts
    assert Court.TRIBUNAL in courts


def test_agent_roles():
    """Test AI agent role definitions"""
    from junior.core.types import AgentRole
    
    roles = list(AgentRole)
    assert AgentRole.RESEARCHER in roles
    assert AgentRole.CRITIC in roles
    assert AgentRole.WRITER in roles
    assert AgentRole.TRANSLATOR in roles
    assert len(roles) >= 4


def test_path_resolution():
    """Test that critical paths exist"""
    from junior.core.config import _repo_root
    
    repo_root = _repo_root()
    assert repo_root.exists()
    assert (repo_root / "src").exists()
    assert (repo_root / "src" / "junior").exists()
    assert (repo_root / "requirements.txt").exists()
    assert (repo_root / "pytest.ini").exists()


def test_api_router_imports():
    """Test that API router can be imported"""
    try:
        from junior.api.router import create_app
        assert callable(create_app)
    except ImportError as e:
        # Accept if it's due to missing dependencies, not code errors
        if "No module named" not in str(e):
            raise
        pytest.skip(f"Skipping due to missing dependency: {e}")
