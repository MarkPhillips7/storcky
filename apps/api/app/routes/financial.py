"""
Financial data API routes.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.services.edgar import EdgarService


router = APIRouter()


class FinancialDataResponse(BaseModel):
    revenue: Optional[float] = None
    grossProfit: Optional[float] = None
    ebitda: Optional[float] = None
    commonSharesOutstanding: Optional[float] = None
    longTermDebt: Optional[float] = None
    quarter: str
    year: Optional[int] = None


@router.get("/financial/{ticker}", response_model=FinancialDataResponse)
async def get_financial_data(ticker: str):
    """
    Get the latest quarter's financial data for a given ticker symbol.
    
    Returns:
    - revenue: Total revenue
    - grossProfit: Gross profit
    - ebitda: Earnings before interest, taxes, depreciation, and amortization
    - commonSharesOutstanding: Total number of common shares outstanding
    - longTermDebt: Long-term debt
    - quarter: Quarter number (1-4)
    - year: Year
    """
    ticker_upper = ticker.upper()
    
    try:
        financial_data = EdgarService.get_financial_data(ticker_upper)
        
        if not financial_data:
            raise HTTPException(
                status_code=404,
                detail=f"Financial data not found for ticker {ticker_upper}"
            )
        
        return FinancialDataResponse(
            revenue=financial_data.get("revenue"),
            grossProfit=financial_data.get("grossProfit"),
            ebitda=financial_data.get("ebitda"),
            commonSharesOutstanding=financial_data.get("commonSharesOutstanding"),
            longTermDebt=financial_data.get("longTermDebt"),
            quarter=financial_data.get("quarter", "N/A"),
            year=financial_data.get("year"),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching financial data: {str(e)}"
        )
