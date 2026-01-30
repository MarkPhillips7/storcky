"""Pytest fixtures for API tests."""
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Return a test client for the FastAPI app."""
    return TestClient(app)
