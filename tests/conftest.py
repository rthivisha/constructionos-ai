import os
import pytest

@pytest.fixture(autouse=True)
def ensure_test_env(monkeypatch):
    """
    Ensure all unit and integration tests run in isolated test environment,
    leaving live PostgreSQL DATABASE_URL active for live runtime scripts and deployments.
    """
    monkeypatch.setenv("DATABASE_URL", "")
