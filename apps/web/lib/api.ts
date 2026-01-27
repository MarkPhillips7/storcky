export interface CompanyInfo {
  name: string
  cik: string
  ticker: string | null
}

export interface Concept {
  id: string
  tag: string
  label: string
  unit: string | null
}

export interface FactPeriod {
  id: string
  start_date: string // ISO date string
  end_date: string // ISO date string
  period_type: string
  accn: string | null
  filed_at: string | null // ISO datetime string
}

export interface CompanyFact {
  concept: string
  fact_period: string
  value: string
}

export interface CompanyFactsResponse {
  company: CompanyInfo
  concepts: Concept[]
  periods: FactPeriod[]
  facts: CompanyFact[]
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export async function fetchFinancialData(ticker: string): Promise<CompanyFactsResponse> {
  const response = await fetch(`${API_BASE_URL}/api/financial/${ticker}`, {
    next: { revalidate: 3600 }, // Revalidate every hour
  })

  if (!response.ok) {
    const error = await response.text()
    throw new Error(`Failed to fetch financial data: ${error}`)
  }

  const data = await response.json()
  return data
}
