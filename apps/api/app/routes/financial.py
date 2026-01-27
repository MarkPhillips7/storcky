"""
Financial data API routes.
"""
from fastapi import APIRouter, HTTPException
from app.services.edgar import EdgarService, CompanyNotFoundError, EdgarUnavailableError
from app.models.schemas import CompanyFactsResponse


router = APIRouter()


@router.get("/financial/{ticker}", response_model=CompanyFactsResponse)
async def get_financial_data(ticker: str):
    """
    Get company financial facts for a given ticker symbol.
    
    Returns CompanyFactsResponse containing:
    - company: Company identification information
    - concepts: List of financial concepts
    - periods: List of fact periods
    - facts: List of company facts linking concepts to periods with values
    """
    ticker_upper = ticker.upper()
    
    try:
        response = EdgarService.get_company_facts(ticker_upper, period_type="quarterly", limit=4)
        return response
    except CompanyNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e)
        )
    except EdgarUnavailableError as e:
        raise HTTPException(
            status_code=503,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching financial data: {str(e)}"
        )
