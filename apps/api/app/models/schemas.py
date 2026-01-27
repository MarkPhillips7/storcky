from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field


class CompanyInfo(BaseModel):
    """Company identification information."""

    name: str
    cik: str
    ticker: Optional[str] = None


class CompanyFact(BaseModel):
    """A single value for a financial fact."""

    concept: str
    value: str


class FactPeriod(BaseModel):
    """A single period/value for a financial fact."""

    id: str = Field(..., description="The fact period ID (e.g., 'Q3 2025')")
    start_date: date
    end_date: date
    period_type: str = Field(
        ..., description="The period type (e.g., 'quarterly', 'annual')"
    )
    accn: Optional[str] = Field(None, description="SEC accession number")
    filed_at: Optional[datetime] = Field(None, description="Filing date")
    facts: list[CompanyFact]


class Concept(BaseModel):
    """A financial concept."""

    tag: str = Field(..., description="The concept tag/identifier (e.g., 'Revenues')")
    label: str = Field(..., description="Human-readable label")
    unit: Optional[str] = Field(
        None, description="Unit of measurement (e.g., 'USD', 'shares')"
    )


class CompanyFactsResponse(BaseModel):
    """Response containing company financial facts."""

    company: CompanyInfo
    concepts: list[Concept] = Field(default_factory=list)
    periods: list[FactPeriod] = Field(default_factory=list)
