import { notFound } from "next/navigation"
import { fetchFinancialData } from "@/lib/api"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

interface FinancialData {
  revenue: number | null
  grossProfit: number | null
  ebitda: number | null
  fullyDilutedShareCount: number | null
  longTermDebt: number | null
  quarter: string
  year: number
}

interface PageProps {
  params: {
    ticker: string
  }
}

export default async function StockPage({ params }: PageProps) {
  const { ticker } = params
  const tickerUpper = ticker.toUpperCase()

  let financialData: FinancialData | null = null
  let error: string | null = null

  try {
    financialData = await fetchFinancialData(tickerUpper)
  } catch (err) {
    error = err instanceof Error ? err.message : "Failed to fetch financial data"
  }

  if (error || !financialData) {
    return (
      <div className="container mx-auto p-8">
        <h1 className="text-4xl font-bold mb-4">{tickerUpper}</h1>
        <Card>
          <CardHeader>
            <CardTitle>Error</CardTitle>
            <CardDescription>
              {error || "Financial data not available"}
            </CardDescription>
          </CardHeader>
        </Card>
      </div>
    )
  }

  const formatCurrency = (value: number | null): string => {
    if (value === null) return "N/A"
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value)
  }

  const formatNumber = (value: number | null): string => {
    if (value === null) return "N/A"
    return new Intl.NumberFormat("en-US").format(value)
  }

  return (
    <div className="container mx-auto p-8">
      <h1 className="text-4xl font-bold mb-8">{tickerUpper}</h1>
      <p className="text-muted-foreground mb-8">
        Latest Quarter: Q{financialData.quarter} {financialData.year}
      </p>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>Revenue</CardTitle>
            <CardDescription>Total revenue for the quarter</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{formatCurrency(financialData.revenue)}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Gross Profit</CardTitle>
            <CardDescription>Gross profit for the quarter</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{formatCurrency(financialData.grossProfit)}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>EBITDA</CardTitle>
            <CardDescription>Earnings before interest, taxes, depreciation, and amortization</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{formatCurrency(financialData.ebitda)}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Fully Diluted Share Count</CardTitle>
            <CardDescription>Total shares outstanding (fully diluted)</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{formatNumber(financialData.fullyDilutedShareCount)}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Long Term Debt</CardTitle>
            <CardDescription>Long-term debt obligations</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{formatCurrency(financialData.longTermDebt)}</p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
