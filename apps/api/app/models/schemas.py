
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field

class CompanyInfo(BaseModel):
    """Company identification information."""
    name: str
    cik: str
    ticker: Optional[str] = None


class FactPeriod(BaseModel):
    """A single period/value for a financial fact."""
    start_date: date
    end_date: date
    value: Decimal
    accn: Optional[str] = Field(None, description="SEC accession number")
    filed_at: Optional[datetime] = Field(None, description="Filing date")


class CompanyFact(BaseModel):
    """A financial fact/metric for a company."""
    tag: str = Field(..., description="The fact tag/identifier (e.g., 'Revenues')")
    label: str = Field(..., description="Human-readable label")
    unit: Optional[str] = Field(None, description="Unit of measurement (e.g., 'USD', 'shares')")
    periods: list[FactPeriod] = Field(default_factory=list)


class CompanyFactsResponse(BaseModel):
    """Response containing company financial facts."""
    company: CompanyInfo
    identifier_type: str = Field(..., description="Whether identifier was 'ticker' or 'cik'")
    facts: list[CompanyFact]


class CompanyFactsSummaryResponse(BaseModel):
    """Condensed summary of key financial metrics."""
    company: CompanyInfo
    latest_revenue: Optional[Decimal] = None
    latest_net_income: Optional[Decimal] = None
    latest_eps: Optional[Decimal] = None
    latest_total_assets: Optional[Decimal] = None
    latest_total_liabilities: Optional[Decimal] = None
    trailing_quarters_revenue: list[Decimal] = Field(default_factory=list)
    as_of_date: Optional[date] = None
    latest_gross_profit: Optional[Decimal] = None
    latest_ebitda: Optional[Decimal] = None
    common_shares_outstanding: Optional[Decimal] = None
    long_term_debt: Optional[Decimal] = None
    quarter: Optional[str] = None
    year: Optional[int] = None
