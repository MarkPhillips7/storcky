"""Smoke tests for the API."""
from unittest.mock import patch
from datetime import date

from app.models.schemas import (
    CompanyFactsResponse,
    CompanyInfo,
    Concept,
    FactPeriod,
    CompanyFact,
)


def test_root(client):
    """Root endpoint returns 200 and expected message."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Storcky API"
    assert data["version"] == "0.1.0"


def test_health(client):
    """Health endpoint returns 200 and healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@patch("app.routes.financial.EdgarService.get_company_facts")
def test_financial_route_404_on_unknown_ticker(mock_get_facts, client):
    """Financial route returns 404 when company not found."""
    from app.services.edgar import CompanyNotFoundError

    mock_get_facts.side_effect = CompanyNotFoundError("Company XYZ not found")

    response = client.get("/api/financial/UNKNOWNTICKER")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@patch("app.routes.financial.EdgarService.get_company_facts")
def test_financial_route_returns_data(mock_get_facts, client):
    """Financial route returns company facts when found."""
    mock_response = CompanyFactsResponse(
        company=CompanyInfo(name="Test Co", cik="0001234567", ticker="TEST"),
        concepts=[Concept(tag="Revenues", label="Revenues", unit="USD")],
        periods=[
            FactPeriod(
                id="Q1 2025",
                start_date=date(2025, 1, 1),
                end_date=date(2025, 3, 31),
                period_type="quarterly",
                accn=None,
                filed_at=None,
                facts=[CompanyFact(concept="Revenues", value="1000000")],
            )
        ],
    )
    mock_get_facts.return_value = mock_response

    response = client.get("/api/financial/TEST")
    assert response.status_code == 200
    data = response.json()
    assert data["company"]["ticker"] == "TEST"
    assert data["company"]["name"] == "Test Co"
