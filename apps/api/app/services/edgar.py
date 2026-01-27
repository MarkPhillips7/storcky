"""
Service for fetching financial data from SEC EDGAR using EdgarTools.
"""

from decimal import Decimal
from datetime import date, datetime
from typing import Optional, Dict, Any
from edgar import Company
from app.models.schemas import (
    CompanyInfo,
    CompanyFact,
    FactPeriod,
    CompanyFactsResponse,
    CompanyFactsSummaryResponse,
)
import pandas as pd
import logging
import json
import os
import httpx

logger = logging.getLogger(__name__)


class CompanyNotFoundError(Exception):
    """Raised when a company cannot be found by identifier."""

    pass


class EdgarUnavailableError(Exception):
    """Raised when Edgar/SEC data is unavailable."""

    pass


def _normalize_cik(cik: str) -> str:
    """Normalize CIK to 10-digit zero-padded string."""
    try:
        cik_int = int(cik)
        return str(cik_int).zfill(10)
    except ValueError:
        return cik


def _is_cik(identifier: str) -> bool:
    """Check if identifier looks like a CIK (numeric)."""
    try:
        int(identifier)
        return True
    except ValueError:
        return False


def _get_convex_url() -> Optional[str]:
    """Get Convex URL from environment variable."""
    url = os.getenv("CONVEX_URL")
    if not url:
        logger.debug("CONVEX_URL environment variable not set")
    else:
        logger.debug(
            f"CONVEX_URL found: {url[:50]}..."
            if len(url) > 50
            else f"CONVEX_URL found: {url}"
        )
    return url


def _query_convex_facts(ticker: str) -> Optional[Dict[str, Any]]:
    """
    Query Convex for cached company facts by ticker.
    Returns the most recent facts data or None if not found.
    """
    convex_url = _get_convex_url()
    if not convex_url:
        logger.debug("CONVEX_URL not set, skipping Convex query")
        return None

    try:
        # Convex HTTP API endpoint for queries
        query_url = f"{convex_url}/api/query"

        # Call the getCompanyFactsByTicker query
        with httpx.Client(timeout=5.0) as client:
            response = client.post(
                query_url,
                json={
                    "path": "companyFacts:getCompanyFactsByTicker",
                    "args": {"ticker": ticker},
                    "format": "json",
                },
            )
            response.raise_for_status()
            result = response.json()

            # Convex HTTP API returns: {"status": "success", "value": {...}, "logLines": [...]}
            if isinstance(result, dict):
                if result.get("status") == "error":
                    logger.warning(f"Convex query error: {result.get('errorMessage')}")
                    return None
                if result.get("status") == "success":
                    value = result.get("value")
                    if value is None:
                        return None
                    return value

            return None
    except Exception as e:
        logger.warning(f"Failed to query Convex for facts: {e}")
        return None


def _store_convex_facts(
    ticker: str, facts_json: Dict[str, Any], filing_date: datetime
) -> bool:
    """
    Store company facts in Convex. Always inserts a new record.
    Returns True if successful, False otherwise.
    """
    convex_url = _get_convex_url()
    if not convex_url:
        logger.debug("CONVEX_URL not set, skipping Convex store")
        return False

    try:
        # Convex HTTP API endpoint for mutations
        mutation_url = f"{convex_url}/api/mutation"

        # Convert filing_date to timestamp (milliseconds)
        filing_timestamp = (
            int(filing_date.timestamp() * 1000)
            if isinstance(filing_date, datetime)
            else int(filing_date)
        )

        # Call the storeCompanyFacts mutation
        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                mutation_url,
                json={
                    "path": "companyFacts:storeCompanyFacts",
                    "args": {
                        "ticker": ticker,
                        "facts": facts_json,
                        "filingDate": filing_timestamp,
                    },
                    "format": "json",
                },
            )
            response.raise_for_status()
            result = response.json()

            # Convex HTTP API returns: {"status": "success", "value": {...}, "logLines": [...]}
            if isinstance(result, dict):
                if result.get("status") == "error":
                    logger.warning(
                        f"Convex mutation error: {result.get('errorMessage')}"
                    )
                    return False
                if result.get("status") == "success":
                    return True

            return False
    except Exception as e:
        logger.warning(f"Failed to store facts in Convex: {e}")
        return False


def _extract_most_recent_filing_date(facts) -> Optional[datetime]:
    """
    Extract the most recent filing_date from the EntityFacts object.
    Returns the most recent filing_date as a datetime, or None if not found.
    """
    if not facts:
        return None

    max_filing_date = None

    try:
        # Query a few key tags to find the most recent filing date
        # We don't need to query all facts, just a sample
        key_tags = [
            "Revenues",
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "NetIncomeLoss",
        ]

        for tag in key_tags:
            try:
                query = (
                    facts.query().by_concept(tag).sort_by("period_end", ascending=False)
                )
                matched = query.execute()
                if matched:
                    for f in matched[:5]:  # Check first 5 results
                        filed = getattr(f, "filing_date", None)
                        if filed:
                            if isinstance(filed, datetime):
                                filing_dt = filed
                            elif isinstance(filed, date):
                                # Convert date to datetime at midnight for comparison
                                filing_dt = datetime.combine(filed, datetime.min.time())
                            elif isinstance(filed, str):
                                try:
                                    filing_dt = datetime.fromisoformat(
                                        filed.replace("Z", "+00:00")
                                    )
                                except:
                                    continue
                            else:
                                continue

                            if max_filing_date is None or filing_dt > max_filing_date:
                                max_filing_date = filing_dt
            except Exception:
                continue

        return max_filing_date
    except Exception as e:
        logger.warning(f"Error extracting filing date: {e}")
        return None


def _serialize_facts_to_json(facts) -> Optional[Dict[str, Any]]:
    """
    Serialize EntityFacts object to a JSON-compatible dictionary.
    Returns None if serialization fails.
    """
    if not facts:
        return None

    try:
        # Try to get the raw JSON representation if available
        if hasattr(facts, "to_dict"):
            return facts.to_dict()
        elif hasattr(facts, "__dict__"):
            # Convert to dict and handle datetime objects
            result = {}
            for key, value in facts.__dict__.items():
                if isinstance(value, datetime):
                    result[key] = value.isoformat()
                elif isinstance(value, date):
                    result[key] = value.isoformat()
                elif hasattr(value, "__dict__"):
                    result[key] = _serialize_facts_to_json(value)
                else:
                    try:
                        json.dumps(value)  # Test if serializable
                        result[key] = value
                    except (TypeError, ValueError):
                        result[key] = str(value)
            return result
        else:
            # Fallback: convert to string representation
            # This is not ideal but ensures we can store something
            return {"_serialized": str(facts)}
    except Exception as e:
        logger.warning(f"Error serializing facts: {e}")
        return None


def _deserialize_facts_from_json(facts_json: Dict[str, Any]):
    """
    Deserialize JSON facts data back to a format that can be used.
    For now, we'll need to reconstruct the EntityFacts-like structure.
    This is a simplified version - in practice, we may need to work with the raw data.
    """
    # For now, return the JSON as-is since we'll process it directly
    # The actual EntityFacts object reconstruction would be complex
    return facts_json


class EdgarService:
    """Service for interacting with SEC EDGAR data."""

    @staticmethod
    def get_company_by_ticker(ticker: str) -> Optional[Company]:
        """Get a company by its ticker symbol."""
        try:
            company = Company(ticker)
            if company.not_found:
                logger.warning(f"Company not found for ticker {ticker}")
                return None
            return company
        except Exception as e:
            logger.error(f"Error fetching company for ticker {ticker}: {e}")
            return None

    @staticmethod
    def get_company_facts(
        identifier: str,
        period_type: Optional[str] = "quarterly",
        limit: Optional[int] = None,
    ) -> CompanyFactsResponse:
        """
        Retrieve financial facts for a company by ticker or CIK.

        Args:
            identifier: Company ticker (e.g., "AAPL") or CIK (e.g., "0000320193")
            period_type: Optional filter - "annual" or "quarterly"
            limit: Optional limit on number of periods per fact

        Returns:
            CompanyFactsResponse with company info and facts

        Raises:
            CompanyNotFoundError: If company cannot be found
            EdgarUnavailableError: If Edgar/SEC is unavailable
        """
        try:
            # Determine if identifier is CIK or ticker
            is_cik = _is_cik(identifier)

            if is_cik:
                cik_int = int(_normalize_cik(identifier))
                company = Company(cik_int)
                identifier_type = "cik"
                cik = str(cik_int).zfill(10)
            else:
                company = Company(identifier)  # ticker; case-insensitive
                identifier_type = "ticker"
                cik = ""  # set below after not_found check

            if company.not_found:
                raise CompanyNotFoundError(f"Company not found: {identifier}")

            if not is_cik:
                cik = str(company.cik).zfill(10)

            # Get ticker for Convex lookup (only if identifier is a ticker)
            ticker_for_cache = identifier.upper() if not is_cik else None

            # Check Convex for cached facts (only for ticker lookups)
            cached_facts_data = None
            cached_filing_date = None
            if ticker_for_cache:
                cached_facts_data = _query_convex_facts(ticker_for_cache)
                if cached_facts_data:
                    cached_filing_date = cached_facts_data.get("filingDate")
                    if cached_filing_date:
                        # Convert timestamp to datetime for comparison
                        cached_filing_date = datetime.fromtimestamp(
                            cached_filing_date / 1000
                        )

            # Get company facts (EntityFacts) - use .facts property
            facts = company.facts
            if not facts:
                raise CompanyNotFoundError(f"Company facts not found: {identifier}")

            # Extract most recent filing date from fresh facts
            current_filing_date = _extract_most_recent_filing_date(facts)

            # Check if we should use cached data or store new data
            should_use_cache = False
            if cached_facts_data and cached_filing_date and current_filing_date:
                # Use cache if cached filing date is >= current filing date
                if cached_filing_date >= current_filing_date:
                    should_use_cache = True
                    logger.info(
                        f"Using cached facts for {ticker_for_cache} (filing date: {cached_filing_date})"
                    )

            # Store facts in Convex if we have a ticker and either:
            # 1. No cached data exists, or
            # 2. Current filing date is more recent than cached
            if ticker_for_cache and (not cached_facts_data or not should_use_cache):
                if current_filing_date:
                    facts_json = _serialize_facts_to_json(facts)
                    if facts_json:
                        # Just for debugging store the JSON in a file
                        # with open(f"facts_{ticker_for_cache}.json", "w") as f:
                        #     json.dump(facts_json, f)
                        facts_llm_json = facts.to_llm_context()
                        with open(f"facts_{ticker_for_cache}_llm.json", "w") as f:
                            json.dump(facts_llm_json, f)
                        _store_convex_facts(
                            ticker_for_cache, facts_json, current_filing_date
                        )
                        logger.info(
                            f"Stored facts in Convex for {ticker_for_cache} (filing date: {current_filing_date})"
                        )

            # Extract company info
            company_info = CompanyInfo(
                name=company.name,
                cik=cik,
                ticker=company.tickers[0] if company.tickers else None,
            )

            # Process facts via EntityFacts query API (no to_pandas)
            facts_list: list[CompanyFact] = []
            key_tags = [
                "Revenues",
                "RevenueFromContractWithCustomerExcludingAssessedTax",
                "NetIncomeLoss",
                "EarningsPerShareBasic",
                "EarningsPerShareDiluted",
                "Assets",
                "Liabilities",
                "StockholdersEquity",
            ]

            for tag in key_tags:
                query = (
                    facts.query().by_concept(tag).sort_by("period_end", ascending=False)
                )
                matched = query.execute()
                if not matched:
                    continue

                periods_list: list[FactPeriod] = []
                label = matched[0].label
                unit = getattr(matched[0], "unit", None) or "us-gaap"

                for f in matched:
                    if limit and len(periods_list) >= limit:
                        break
                    if period:
                        fp = (getattr(f, "fiscal_period", "") or "").upper()
                        if period == "annual" and fp != "FY":
                            continue
                        if period == "quarterly" and fp not in ("Q1", "Q2", "Q3", "Q4"):
                            continue

                    val = getattr(f, "numeric_value", None)
                    if val is None:
                        continue

                    end_d = getattr(f, "period_end", None)
                    start_d = getattr(f, "period_start", None) or end_d
                    if not end_d:
                        continue

                    accn = getattr(f, "accession", None)
                    filed = getattr(f, "filing_date", None)
                    try:
                        start = (
                            start_d.date() if isinstance(start_d, datetime) else start_d
                        )
                        end = end_d.date() if isinstance(end_d, datetime) else end_d
                        periods_list.append(
                            FactPeriod(
                                start_date=start,
                                end_date=end,
                                value=Decimal(str(val)),
                                accn=str(accn) if accn else None,
                                filed_at=filed,
                            )
                        )
                    except (ValueError, AttributeError, TypeError):
                        continue

                if periods_list:
                    facts_list.append(
                        CompanyFact(
                            tag=tag, label=label, unit=unit, periods=periods_list
                        )
                    )

            return CompanyFactsResponse(
                company=company_info,
                identifier_type=identifier_type,
                facts=facts_list,
            )

        except Exception as e:
            if isinstance(e, (CompanyNotFoundError, EdgarUnavailableError)):
                raise

            # Try to determine error type
            error_msg = str(e).lower()
            if "not found" in error_msg or "no company" in error_msg:
                raise CompanyNotFoundError(f"Company not found: {identifier}") from e

            # Assume network/availability issue
            raise EdgarUnavailableError(f"Edgar/SEC unavailable: {str(e)}") from e

    # @staticmethod
    # def get_company_facts_summary(identifier: str) -> CompanyFactsSummaryResponse:
    #     """
    #     Get a condensed summary of key financial metrics.

    #     Args:
    #         identifier: Company ticker or CIK

    #     Returns:
    #         CompanyFactsSummaryResponse with key metrics
    #     """
    #     facts_response = EdgarService.get_company_facts(identifier, limit=4)

    #     company_info = facts_response.company

    #     # Extract key metrics
    #     latest_revenue = None
    #     latest_gross_profit = None
    #     latest_ebitda = None
    #     latest_common_shares_outstanding = None
    #     latest_long_term_debt = None
    #     latest_quarter = None
    #     latest_year = None
    #     latest_net_income = None
    #     latest_eps = None
    #     latest_total_assets = None
    #     latest_total_liabilities = None
    #     trailing_quarters_revenue: list[Decimal] = []
    #     as_of_date: Optional[date] = None

    #     for fact in facts_response.facts:
    #         if not fact.periods:
    #             continue

    #         latest_period = fact.periods[0]
    #         if not as_of_date or latest_period.end_date > as_of_date:
    #             as_of_date = latest_period.end_date
    #             latest_quarter = "Q3"  # latest_period.end_date.quarter
    #             latest_year = 2025  # latest_period.end_date.year

    #         if (
    #             fact.tag == "Revenues"
    #             or fact.tag == "RevenueFromContractWithCustomerExcludingAssessedTax"
    #         ):
    #             # Unit is now namespace, but we'll accept any for revenue
    #             latest_revenue = latest_period.value
    #             # Get trailing quarters
    #             quarterly_periods = [
    #                 p for p in fact.periods if p.end_date <= as_of_date
    #             ][:4]
    #             trailing_quarters_revenue = [p.value for p in quarterly_periods]

    #         elif fact.tag == "NetIncomeLoss":
    #             latest_net_income = latest_period.value

    #         elif fact.tag in ["EarningsPerShareBasic", "EarningsPerShareDiluted"]:
    #             latest_eps = latest_period.value

    #         elif fact.tag == "Assets":
    #             latest_total_assets = latest_period.value

    #         elif fact.tag == "Liabilities":
    #             latest_total_liabilities = latest_period.value
    #         elif fact.tag == "GrossProfit":
    #             latest_gross_profit = latest_period.value
    #         elif fact.tag == "EBITDA":
    #             latest_ebitda = latest_period.value
    #         elif fact.tag == "CommonStockSharesOutstanding":
    #             latest_common_shares_outstanding = latest_period.value
    #         elif fact.tag == "LongTermDebt":
    #             latest_long_term_debt = latest_period.value

    #     return CompanyFactsSummaryResponse(
    #         company=company_info,
    #         latest_revenue=latest_revenue,
    #         latest_net_income=latest_net_income,
    #         latest_eps=latest_eps,
    #         latest_total_assets=latest_total_assets,
    #         latest_total_liabilities=latest_total_liabilities,
    #         trailing_quarters_revenue=trailing_quarters_revenue,
    #         as_of_date=as_of_date,
    #         latest_gross_profit=latest_gross_profit,
    #         latest_ebitda=latest_ebitda,
    #         common_shares_outstanding=latest_common_shares_outstanding,
    #         long_term_debt=latest_long_term_debt,
    #         quarter=latest_quarter,
    #         year=latest_year,
    #     )

    # @staticmethod
    # def get_financial_data(ticker: str) -> Optional[Dict[str, Any]]:
    #     """Get financial data for a given ticker symbol."""
    #     company = EdgarService.get_company_by_ticker(ticker)
    #     if not company:
    #         return None

    #     facts = EdgarService.get_company_facts_summary(ticker)

    #     return {
    #         "revenue": facts.latest_revenue,
    #         "grossProfit": facts.latest_gross_profit,
    #         "ebitda": facts.latest_ebitda,
    #         "commonSharesOutstanding": facts.common_shares_outstanding,
    #         "longTermDebt": facts.long_term_debt,
    #         "quarter": facts.quarter,
    #         "year": facts.year,
    #     }
    #     # return EdgarService.get_latest_quarter_financials(company)
