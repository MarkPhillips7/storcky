"""
Service for fetching financial data from SEC EDGAR using EdgarTools.
"""
from typing import Optional, Dict, Any
from edgar import Company
import pandas as pd


class EdgarService:
    """Service for interacting with SEC EDGAR data."""

    @staticmethod
    def get_company_by_ticker(ticker: str) -> Optional[Company]:
        """Get a company by its ticker symbol."""
        try:
            company = Company(ticker)
            return company
        except Exception as e:
            print(f"Error fetching company for ticker {ticker}: {e}")
            return None

    @staticmethod
    def get_latest_quarter_financials(company: Company) -> Optional[Dict[str, Any]]:
        """Get the latest quarter's financial data."""
        try:
            # Get quarterly financials from the latest 10-Q
            financials = company.get_quarterly_financials()
            
            if not financials:
                # Fallback to annual financials if no quarterly available
                financials = company.get_financials()
                if not financials:
                    return None

            # Financials object has income, balance_sheet, and cash_flow as DataFrames
            income_stmt = financials.income
            balance_sheet = financials.balance_sheet
            
            if income_stmt is None or balance_sheet is None:
                return None

            # Get the latest period (first column in DataFrame)
            if income_stmt.empty or balance_sheet.empty:
                return None

            # Get the first column which should be the latest period
            latest_period_col = income_stmt.columns[0] if len(income_stmt.columns) > 0 else None
            
            if latest_period_col is None:
                return None

            # Helper function to safely get value from DataFrame
            def get_value(df: pd.DataFrame, search_terms: list) -> Optional[float]:
                """Search for a value in DataFrame using multiple possible row names."""
                if df is None or df.empty:
                    return None
                
                for term in search_terms:
                    # Try exact match first
                    if term in df.index:
                        value = df.loc[term, latest_period_col]
                        if pd.notna(value):
                            try:
                                return float(value)
                            except (ValueError, TypeError):
                                pass
                    
                    # Try case-insensitive partial match
                    matching_rows = df.index[df.index.str.contains(term, case=False, na=False)]
                    if len(matching_rows) > 0:
                        value = df.loc[matching_rows[0], latest_period_col]
                        if pd.notna(value):
                            try:
                                return float(value)
                            except (ValueError, TypeError):
                                pass
                return None

            # Extract financial metrics
            revenue = get_value(income_stmt, [
                "Revenues", "Revenue", "TotalRevenue", "NetSales", 
                "SalesRevenueNet", "SalesAndRevenue"
            ])
            
            gross_profit = get_value(income_stmt, [
                "GrossProfit", "GrossProfitLoss", "GrossIncome"
            ])
            
            ebitda = get_value(income_stmt, [
                "EBITDA", "EarningsBeforeInterestTaxesDepreciationAndAmortization"
            ])
            
            # If EBITDA not found, try to calculate from components
            if ebitda is None:
                operating_income = get_value(income_stmt, [
                    "OperatingIncomeLoss", "OperatingIncome", "IncomeFromOperations"
                ])
                depreciation = get_value(income_stmt, [
                    "DepreciationAndAmortization", "DepreciationAmortizationAndAccretion"
                ])
                if operating_income is not None and depreciation is not None:
                    ebitda = operating_income + depreciation

            fully_diluted_shares = get_value(balance_sheet, [
                "WeightedAverageNumberOfDilutedSharesOutstanding",
                "WeightedAverageNumberOfSharesOutstandingDiluted",
                "SharesOutstandingDiluted",
                "CommonStockSharesOutstanding"
            ])
            
            long_term_debt = get_value(balance_sheet, [
                "LongTermDebt", "LongTermDebtAndCapitalLeaseObligation",
                "LongTermDebtNoncurrent", "DebtLongtermAndShorttermCombinedAmount"
            ])

            # Extract quarter and year from period column name or filing date
            quarter = None
            year = None
            
            # Try to get from latest 10-Q filing
            try:
                latest_10q = company.latest_tenq
                if latest_10q and hasattr(latest_10q, 'filing_date'):
                    filing_date = latest_10q.filing_date
                    if filing_date:
                        year = filing_date.year
                        quarter = str((filing_date.month - 1) // 3 + 1)
            except:
                pass

            # If we couldn't get from filing, try to parse from column name
            if not quarter or not year:
                if latest_period_col:
                    # Try to parse date format like "2024-03-31"
                    if isinstance(latest_period_col, str) and "-" in latest_period_col:
                        try:
                            parts = latest_period_col.split("-")
                            if len(parts) >= 2:
                                year = int(parts[0])
                                month = int(parts[1])
                                quarter = str((month - 1) // 3 + 1)
                        except:
                            pass

            return {
                "revenue": revenue,
                "grossProfit": gross_profit,
                "ebitda": ebitda,
                "fullyDilutedShareCount": fully_diluted_shares,
                "longTermDebt": long_term_debt,
                "quarter": quarter or "N/A",
                "year": year,
            }

        except Exception as e:
            print(f"Error fetching financials: {e}")
            import traceback
            traceback.print_exc()
            return None

    @staticmethod
    def get_financial_data(ticker: str) -> Optional[Dict[str, Any]]:
        """Get financial data for a given ticker symbol."""
        company = EdgarService.get_company_by_ticker(ticker)
        if not company:
            return None
        
        return EdgarService.get_latest_quarter_financials(company)
