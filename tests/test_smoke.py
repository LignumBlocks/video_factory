import pytest
from src.orchestrator import RunOrchestrator

def test_smoke():
    """Dummy test to ensure pytest configuration is correct."""
    assert True

def test_imports():
    """Ensure core modules can be imported."""
    try:
        from src.foundation.manifest import RunManifest
        from src.orchestrator import RunOrchestrator
        assert True
    except ImportError as e:
        pytest.fail(f"Import failed: {e}")
