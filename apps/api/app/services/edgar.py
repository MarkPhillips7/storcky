"""
Service for fetching financial data from SEC EDGAR using EdgarTools.
"""
from typing import Optional, Dict, Any
from edgar import Company
import pandas as pd
import logging

logger = logging.getLogger(__name__)


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
    def get_latest_quarter_financials(company: Company) -> Optional[Dict[str, Any]]:
        """Get the latest quarter's financial data."""
        try:
            # Try to get quarterly financials from the latest 10-Q
            # First, try using the financials property directly
            financials = None
            
            # Try quarterly first
            try:
                quarterly = company.get_quarterly_financials()
                if quarterly:
                    financials = quarterly
            except:
                pass
            
            # Fallback to annual financials
            if not financials:
                try:
                    financials = company.get_financials()
                except:
                    pass
            
            # If still no financials, try the property directly
            if not financials:
                try:
                    financials = company.financials
                except:
                    pass
            
            if not financials:
                logger.warning("Could not retrieve financials from any source")
                return None

            # Check what attributes/methods are available
            logger.info(f"Financials object type: {type(financials)}")
            logger.info(f"Financials object has 'income': {hasattr(financials, 'income')}")
            logger.info(f"Financials object has 'income_statement': {hasattr(financials, 'income_statement')}")
            logger.info(f"Financials object has 'balance_sheet': {hasattr(financials, 'balance_sheet')}")
            # Log all attributes that might be relevant
            attrs = [attr for attr in dir(financials) if not attr.startswith('_') and ('income' in attr.lower() or 'balance' in attr.lower() or 'cash' in attr.lower())]
            logger.info(f"Relevant Financials attributes: {attrs}")
            
            # Try to access income statement - could be property or method
            income_stmt = None
            balance_sheet = None
            
            # income_statement is a method, not a property
            if hasattr(financials, 'income_statement'):
                income_stmt_attr = getattr(financials, 'income_statement')
                if callable(income_stmt_attr):
                    income_stmt = income_stmt_attr()
                else:
                    income_stmt = income_stmt_attr
            elif hasattr(financials, 'income'):
                income_attr = getattr(financials, 'income')
                if callable(income_attr):
                    income_stmt = income_attr()
                else:
                    income_stmt = income_attr
            
            # balance_sheet might also be a method
            if hasattr(financials, 'balance_sheet'):
                balance_sheet_attr = getattr(financials, 'balance_sheet')
                if callable(balance_sheet_attr):
                    balance_sheet = balance_sheet_attr()
                else:
                    balance_sheet = balance_sheet_attr
            
            if income_stmt is None or balance_sheet is None:
                logger.error(f"Could not access income statement or balance sheet. Income: {income_stmt is not None}, Balance: {balance_sheet is not None}")
                return None

            # Convert Statement objects to DataFrames if needed
            if hasattr(income_stmt, 'to_dataframe'):
                logger.info("Converting income statement Statement to DataFrame")
                income_stmt = income_stmt.to_dataframe()
            if hasattr(balance_sheet, 'to_dataframe'):
                logger.info("Converting balance sheet Statement to DataFrame")
                balance_sheet = balance_sheet.to_dataframe()

            # Ensure they're DataFrames
            if not isinstance(income_stmt, pd.DataFrame):
                logger.error(f"Income statement is not a DataFrame: {type(income_stmt)}")
                return None
            if not isinstance(balance_sheet, pd.DataFrame):
                logger.error(f"Balance sheet is not a DataFrame: {type(balance_sheet)}")
                return None

            # Get the latest period (first column in DataFrame)
            if income_stmt.empty or balance_sheet.empty:
                logger.warning("Income statement or balance sheet is empty")
                return None

            # Get the first column which should be the latest period
            # Financials DataFrames typically have date columns
            if len(income_stmt.columns) == 0:
                logger.warning("Income statement has no columns")
                return None
            
            latest_period_col = income_stmt.columns[0]
            
            # Log DataFrame structure for debugging
            logger.info(f"Income statement shape: {income_stmt.shape}")
            logger.info(f"Income statement index type: {type(income_stmt.index)}")
            logger.info(f"Income statement index dtype: {income_stmt.index.dtype}")
            logger.info(f"Income statement columns: {list(income_stmt.columns)}")
            logger.info(f"Income statement index sample (first 5): {list(income_stmt.index[:5])}")
            logger.info(f"Using latest period column: {latest_period_col}")

            # Helper function to safely get value from DataFrame
            def get_value(df: pd.DataFrame, search_terms: list) -> Optional[float]:
                """Search for a value in DataFrame using multiple possible row names."""
                if df is None or df.empty:
                    return None
                
                # Check if index is string type for string operations
                index_is_string = False
                if len(df.index) > 0:
                    try:
                        first_idx = df.index[0]
                        index_is_string = isinstance(first_idx, str) or (hasattr(df.index, 'dtype') and df.index.dtype == 'object')
                    except:
                        pass
                
                for term in search_terms:
                    # Try exact match first (works for both string and numeric indices)
                    try:
                        if term in df.index:
                            value = df.loc[term, latest_period_col]
                            if pd.notna(value):
                                try:
                                    return float(value)
                                except (ValueError, TypeError):
                                    pass
                    except (KeyError, TypeError):
                        pass
                    
                    # Try case-insensitive partial match (only if index is string)
                    if index_is_string:
                        try:
                            # Convert index to string for comparison
                            str_index = df.index.astype(str)
                            matching_rows = df.index[str_index.str.contains(term, case=False, na=False)]
                            if len(matching_rows) > 0:
                                value = df.loc[matching_rows[0], latest_period_col]
                                if pd.notna(value):
                                    try:
                                        return float(value)
                                    except (ValueError, TypeError):
                                        pass
                        except (AttributeError, TypeError, ValueError) as e:
                            logger.debug(f"String search failed for {term}: {e}")
                            pass
                    
                    # If index is numeric, search in all string representations
                    if not index_is_string:
                        try:
                            # Convert all index values to string and search
                            for idx in df.index:
                                idx_str = str(idx).lower()
                                if term.lower() in idx_str:
                                    value = df.loc[idx, latest_period_col]
                                    if pd.notna(value):
                                        try:
                                            return float(value)
                                        except (ValueError, TypeError):
                                            pass
                        except Exception as e:
                            logger.debug(f"Index search failed for {term}: {e}")
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
                if latest_10q:
                    # Try different ways to get the filing date
                    if hasattr(latest_10q, 'filing_date'):
                        filing_date = latest_10q.filing_date
                    elif hasattr(latest_10q, 'date'):
                        filing_date = latest_10q.date
                    else:
                        filing_date = None
                    
                    if filing_date:
                        if hasattr(filing_date, 'year'):
                            year = filing_date.year
                            quarter = str((filing_date.month - 1) // 3 + 1)
                        elif isinstance(filing_date, str):
                            # Parse string date
                            from datetime import datetime
                            try:
                                dt = datetime.fromisoformat(filing_date.replace('Z', '+00:00'))
                                year = dt.year
                                quarter = str((dt.month - 1) // 3 + 1)
                            except:
                                pass
            except Exception as e:
                logger.debug(f"Could not get quarter/year from filing: {e}")
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
            logger.error(f"Error fetching financials: {e}", exc_info=True)
            return None

    @staticmethod
    def get_financial_data(ticker: str) -> Optional[Dict[str, Any]]:
        """Get financial data for a given ticker symbol."""
        company = EdgarService.get_company_by_ticker(ticker)
        if not company:
            return None
        
        return EdgarService.get_latest_quarter_financials(company)
