"""Pytest fixtures for API tests."""
import pytest
import httpx
from httpx import ASGITransport

from app.main import app


@pytest.fixture
async def client():
    """Return an async test client for the FastAPI app."""
    # Starlette TestClient is incompatible with httpx 0.28+; use AsyncClient
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test"
    ) as ac:
        yield ac
