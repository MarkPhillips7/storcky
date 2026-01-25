interface FinancialData {
  revenue: number | null
  grossProfit: number | null
  ebitda: number | null
  fullyDilutedShareCount: number | null
  longTermDebt: number | null
  quarter: string
  year: number
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export async function fetchFinancialData(ticker: string): Promise<FinancialData> {
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
