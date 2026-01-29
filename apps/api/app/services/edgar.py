"""
Service for fetching financial data from SEC EDGAR using EdgarTools.
"""

from decimal import Decimal
from datetime import date, datetime
from typing import Optional, Dict, Any, Tuple
from edgar import Company
from app.models.schemas import (
    CompanyInfo,
    CompanyFact,
    FactPeriod,
    Concept,
    CompanyFactsResponse,
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


def _query_convex_facts(
    ticker: str,
) -> Tuple[Optional[CompanyFactsResponse], Optional[datetime]]:
    """
    Query Convex for cached company facts by ticker.
    Returns a tuple of (CompanyFactsResponse, filing_date) or (None, None) if not found.
    """
    convex_url = _get_convex_url()
    if not convex_url:
        logger.debug("CONVEX_URL not set, skipping Convex query")
        return None, None

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
                    return None, None
                if result.get("status") == "success":
                    value = result.get("value")
                    if value is None:
                        return None, None

                    # Extract filing date
                    filing_date_ts = value.get("filingDate")
                    filing_date = None
                    if filing_date_ts:
                        filing_date = datetime.fromtimestamp(filing_date_ts / 1000)

                    # Deserialize the CompanyFactsResponse from the cached data
                    facts_data = value.get("facts")
                    if facts_data:
                        facts_response = _deserialize_company_facts_response(facts_data)
                        return facts_response, filing_date
                    return None, None

            return None, None
    except Exception as e:
        logger.warning(f"Failed to query Convex for facts: {e}")
        return None, None


def _store_convex_facts(
    ticker: str, response: CompanyFactsResponse, filing_date: datetime
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

        # Serialize CompanyFactsResponse to JSON
        facts_json = _serialize_company_facts_response(response)

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


def _generate_period_id(fiscal_period: str, end_date: date) -> str:
    """
    Generate a period ID in the format "Q1 2024" or "FY 2023".

    Args:
        fiscal_period: The fiscal period string (Q1, Q2, Q3, Q4, FY, etc.)
        end_date: The period end date

    Returns:
        Period ID string (e.g., "Q1 2024", "FY 2023")
    """
    fp = fiscal_period.upper().strip() if fiscal_period else "UNKNOWN"
    year = end_date.year
    return f"{fp} {year}"


def _fact_log_context(
    f,
    tag: str,
    period_id: str,
    val: Any,
    accn: Any,
    filed: Any,
    fp: str,
    start: Optional[date] = None,
    end: Optional[date] = None,
) -> Dict[str, Any]:
    """Build a loggable dict of fact attributes for dedup debugging."""
    ctx: Dict[str, Any] = {
        "concept": tag,
        "period_id": period_id,
        "value": str(val) if val is not None else None,
        "unit": getattr(f, "unit", None),
        "accession": str(accn) if accn is not None else None,
        "filing_date": str(filed) if filed is not None else None,
        "fiscal_period": fp,
        "period_start": str(start) if start is not None else None,
        "period_end": str(end) if end is not None else None,
    }
    for attr in ("form", "dimensions", "segment", "context_id"):
        v = getattr(f, attr, None)
        if v is not None:
            ctx[attr] = str(v) if not isinstance(v, (dict, list)) else v
    return ctx


def _serialize_company_facts_response(response: CompanyFactsResponse) -> Dict[str, Any]:
    """
    Serialize CompanyFactsResponse to JSON-compatible dictionary.

    Args:
        response: The CompanyFactsResponse to serialize

    Returns:
        JSON-compatible dictionary
    """
    return response.model_dump(mode="json")


def _deserialize_company_facts_response(
    data: Dict[str, Any],
) -> Optional[CompanyFactsResponse]:
    """
    Deserialize JSON dictionary to CompanyFactsResponse.

    Args:
        data: JSON dictionary containing CompanyFactsResponse data

    Returns:
        CompanyFactsResponse object or None if deserialization fails
    """
    try:
        # Normalize the data to ensure periods have facts field
        # This handles cases where data stored in Convex might be missing facts
        if "periods" in data and isinstance(data["periods"], list):
            for period in data["periods"]:
                if isinstance(period, dict) and "facts" not in period:
                    logger.debug(
                        f"Adding missing facts field to period: {period.get('id', 'unknown')}"
                    )
                    period["facts"] = []

        # Normalize concepts to ensure label field is present
        # This handles cases where data stored in Convex might have None labels
        if "concepts" in data and isinstance(data["concepts"], list):
            for concept in data["concepts"]:
                if isinstance(concept, dict):
                    if "label" not in concept or concept["label"] is None:
                        # Use tag as fallback label
                        tag = concept.get("tag", "Unknown")
                        concept["label"] = tag.split(":")[-1] if ":" in tag else tag
                        logger.debug(f"Adding missing label to concept: {tag}")

        return CompanyFactsResponse.model_validate(data)
    except Exception as e:
        logger.warning(f"Failed to deserialize CompanyFactsResponse: {e}")
        # Log the problematic data structure for debugging
        if "periods" in data:
            logger.debug(
                f"Periods count: {len(data['periods']) if isinstance(data['periods'], list) else 'not a list'}"
            )
            for i, period in enumerate(
                data.get("periods", [])[:2]
            ):  # Log first 2 periods
                if isinstance(period, dict):
                    logger.debug(f"Period {i} keys: {list(period.keys())}")
        return None


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
                cik = str(cik_int).zfill(10)
            else:
                company = Company(identifier)  # ticker; case-insensitive
                cik = ""  # set below after not_found check

            if company.not_found:
                raise CompanyNotFoundError(f"Company not found: {identifier}")

            if not is_cik:
                cik = str(company.cik).zfill(10)

            # Get ticker for Convex lookup (only if identifier is a ticker)
            ticker_for_cache = identifier.upper() if not is_cik else None

            # Check Convex for cached facts (only for ticker lookups)
            cached_response = None
            cached_filing_date = None
            if ticker_for_cache:
                cached_response, cached_filing_date = _query_convex_facts(
                    ticker_for_cache
                )

            # Get company facts (EntityFacts) - use .facts property
            facts = company.facts
            if not facts:
                raise CompanyNotFoundError(f"Company facts not found: {identifier}")

            # Extract most recent filing date from fresh facts
            current_filing_date = _extract_most_recent_filing_date(facts)

            # Check if we should use cached data
            should_use_cache = False
            # if cached_response and cached_filing_date and current_filing_date:
            #     # Use cache if cached filing date is >= current filing date
            #     if cached_filing_date >= current_filing_date:
            #         should_use_cache = True
            #         logger.info(
            #             f"Using cached facts for {ticker_for_cache} (filing date: {cached_filing_date})"
            #         )

            # Extract company info
            company_info = CompanyInfo(
                name=company.name,
                cik=cik,
                ticker=company.tickers[0] if company.tickers else None,
            )

            # If we have cached data and it's current, return it
            if cached_response and should_use_cache:
                return cached_response

            # Process facts via EntityFacts query API
            # Build concepts, periods, and facts separately
            concepts_dict: Dict[str, Concept] = {}  # keyed by concept tag
            periods_dict: Dict[str, FactPeriod] = {}  # keyed by period ID
            # Deduplicate facts per period: period_id -> concept -> CompanyFact
            period_facts_dict: Dict[str, Dict[str, CompanyFact]] = {}

            # Comments after tags reflect EOS Energy's latest 10-Q labels
            key_tags = [
                # Under "UNAUDITED CONDENSED CONSOLIDATED BALANCE SHEETS"
                "us-gaap:Assets",  # Total assets
                "us-gaap:Liabilities",  # Total liabilities
                "us-gaap:TotalEquity",
                # EOSE seems to have stopped using this:
                # "us-gaap:DebtInstrumentInterestRateEffectivePercentage",  # StockholdersEquity",
                # Under "UNAUDITED CONDENSED CONSOLIDATED STATEMENTS OF OPERATIONS AND COMPREHENSIVE LOSS":
                "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",  # Revenue
                "us-gaap:CostOfGoodsAndServicesSold",  # Cost of Goods Sold
                "us-gaap:GrossProfit",  # Gross Profit
                "us-gaap:ResearchAndDevelopmentExpense",  # Research and Development Expenses
                "us-gaap:SellingGeneralAndAdministrativeExpense",  # Selling, General, and Administrative Expenses
                # shows up for EOSE but perhaps don't use (just have "Other Expenses")
                "us-gaap:ImpairmentOfLongLivedAssetsHeldForUse",  # Loss from write-down of property, plant and equipment
                "us-gaap:CostsAndExpenses",  # Total operating expenses
                "us-gaap:OperatingIncomeLoss",  # Operating Loss
                # EOSE seems to have used this in 2020 and 2021 but not since then:
                # "us-gaap:InterestExpenseDebt",
                # Next 2 tags not found for EOSE. See "Segment Reporting" below.
                # Interest expense, net
                # "us-gaap:InterestExpenseRelatedParty", # Interest income (expense) - related party
                "us-gaap:LiabilitiesFairValueAdjustment",  # Change in fair value of debt - related party
                "us-gaap:FairValueAdjustmentOfWarrants",  # Change in fair value of warrants
                "us-gaap:EmbeddedDerivativeGainLossOnEmbeddedDerivativeNet",  # Change in fair value of derivatives - related parties
                "us-gaap:GainsLossesOnExtinguishmentOfDebt",  # (Loss) gain on debt extinguishment
                # Other expense
                # Loss before income taxes
                "us-gaap:IncomeTaxExpenseBenefit",  # Income tax expense (benefit)
                "us-gaap:NetIncomeLoss",  # Net Loss attributable to shareholders
                # Remeasurement of Preferred Stock - related party
                # Down round deemed dividend
                # Net Loss attributable to common shareholders
                # Change in fair value of debt - credit risk - related party
                # Foreign currency translation adjustment
                "us-gaap:ComprehensiveIncomeNetOfTax",  # Comprehensive Loss attributable to common shareholders
                "us-gaap:WeightedAverageNumberOfSharesOutstandingBasic",  # Weighted average shares of common stock Basic
                # "us-gaap:WeightedAverageNumberOfDilutedSharesOutstanding", # Weighted average shares of common stock Diluted
                # No tag found for these under "UNAUDITED CONDENSED CONSOLIDATED STATEMENTS OF OPERATIONS AND COMPREHENSIVE LOSS":
                # Interest expense, net
                # "us-gaap:InterestExpenseRelatedParty", # Interest income (expense) - related party
                # Under "Segment Reporting":
                "us-gaap:DepreciationAndAmortization",  # Depreciation and Amortization
                # EOSE shows "Interest expense, net" and "Interest income (expense) - related party" under "UNAUDITED CONDENSED CONSOLIDATED STATEMENTS OF OPERATIONS AND COMPREHENSIVE LOSS"
                # but "Interest income" and "Interest expense" under "Segment Reporting."
                # These values do not match but match when added together.
                "us-gaap:InvestmentIncomeInterest",  # Interest income
                "us-gaap:InterestExpenseNonoperating",  # Interest expense
                "us-gaap:SegmentExpenditureAdditionToLongLivedAssets",  # Capital Expenditures
                # No tag found for these under "Segment Reporting":
                # Product revenue
                # Service revenue
            ]

            for tag in key_tags:
                query = (
                    facts.query()
                    .by_concept(tag, True)
                    .sort_by("period_end", ascending=False)
                )
                matched = query.execute()
                if not matched:
                    continue

                # Get concept metadata from first match
                label = getattr(matched[0], "label", None)
                # Fallback to tag if label is None or empty
                if not label:
                    # Use tag as fallback, removing namespace prefix if present
                    label = tag.split(":")[-1] if ":" in tag else tag
                unit = getattr(matched[0], "unit", None) or "us-gaap"

                # Create or get concept
                if tag not in concepts_dict:
                    concepts_dict[tag] = Concept(
                        tag=tag,
                        label=label,
                        unit=unit,
                    )

                # Process each fact value
                period_count = 0
                for f in matched:
                    if limit and period_count >= limit:
                        break

                    # Filter by period_type if specified
                    if period_type:
                        fp = (getattr(f, "fiscal_period", "") or "").upper()
                        if period_type == "annual" and fp != "FY":
                            continue
                        if period_type == "quarterly" and fp not in (
                            "Q1",
                            "Q2",
                            "Q3",
                            "Q4",
                            "FY",
                        ):
                            continue

                    val = getattr(f, "numeric_value", None)
                    if val is None:
                        continue

                    end_d = getattr(f, "period_end", None)
                    start_d = getattr(f, "period_start", None) or end_d
                    if not end_d:
                        continue

                    if period_type == "quarterly" and end_d.month - start_d.month > 3:
                        continue

                    accn = getattr(f, "accession", None)
                    filed = getattr(f, "filing_date", None)
                    fp = (getattr(f, "fiscal_period", "") or "").upper()

                    try:
                        start = (
                            start_d.date() if isinstance(start_d, datetime) else start_d
                        )
                        end = end_d.date() if isinstance(end_d, datetime) else end_d

                        # Determine period_type from fiscal_period
                        fact_period_type = "annual" if fp == "FY" else "quarterly"

                        # Generate period ID
                        period_id = _generate_period_id(fp, end)

                        # Create or get period
                        if period_id not in periods_dict:
                            periods_dict[period_id] = FactPeriod(
                                id=period_id,
                                start_date=start,
                                end_date=end,
                                period_type=fact_period_type,
                                accn=str(accn) if accn else None,
                                filed_at=filed,
                                facts=[],
                            )
                            period_facts_dict[period_id] = {}

                        facts_for_period = period_facts_dict[period_id]
                        fact = CompanyFact(concept=tag, value=str(val))
                        # print("f: {f}")
                        # log_ctx = _fact_log_context(
                        #     f, tag, period_id, val, accn, filed, fp, start, end
                        # )

                        if tag in facts_for_period:
                            existing = facts_for_period[tag]
                            if existing.value != fact.value:
                                logger.error(
                                    "Duplicate CompanyFact for same concept '%s' in period '%s': "
                                    "stored value '%s' vs new value '%s'",
                                    tag,
                                    period_id,
                                    existing.value,
                                    fact.value,
                                )
                                # logger.info(
                                #     "CompanyFact skipped (conflict). New fact details: %s",
                                #     log_ctx,
                                # )
                            # else:
                            # logger.info(
                            #     "CompanyFact skipped (duplicate, same value): %s",
                            #     log_ctx,
                            # )
                        else:
                            facts_for_period[tag] = fact
                            # logger.info(
                            #     "CompanyFact stored (first occurrence): %s", log_ctx
                            # )

                        period_count += 1
                    except (ValueError, AttributeError, TypeError) as e:
                        logger.debug(f"Error processing fact: {e}")
                        continue

            # Populate each period's facts from deduplicated dict
            for period_id, period in periods_dict.items():
                period.facts = list(period_facts_dict.get(period_id, {}).values())

            # Build the response
            response = CompanyFactsResponse(
                company=company_info,
                concepts=list(concepts_dict.values()),
                periods=list(periods_dict.values()),
            )

            # Store response in Convex if we have a ticker and either:
            # 1. No cached data exists, or
            # 2. Current filing date is more recent than cached
            if ticker_for_cache and current_filing_date and not should_use_cache:
                # Store the CompanyFactsResponse
                _store_convex_facts(ticker_for_cache, response, current_filing_date)
                logger.info(
                    f"Stored facts in Convex for {ticker_for_cache} (filing date: {current_filing_date})"
                )

            return response

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
