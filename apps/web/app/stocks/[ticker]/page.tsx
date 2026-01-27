import { notFound } from "next/navigation"
import { fetchFinancialData, CompanyFactsResponse, Concept, CompanyFact, FactPeriod } from "@/lib/api"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

interface PageProps {
  params: {
    ticker: string
  }
}

function formatValue(value: string, unit: string | null): string {
  const numValue = parseFloat(value)
  if (isNaN(numValue)) return value

  // Check if it's a currency unit
  if (unit?.toLowerCase().includes("usd") || unit?.toLowerCase().includes("currency")) {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(numValue)
  }

  // Check if it's shares
  if (unit?.toLowerCase().includes("share")) {
    return new Intl.NumberFormat("en-US").format(numValue)
  }

  // Default number formatting
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(numValue)
}

function getLatestFactForConcept(
  conceptId: string,
  facts: CompanyFact[],
  periods: FactPeriod[]
): { fact: CompanyFact; period: FactPeriod | null } | null {
  // Find all facts for this concept
  const conceptFacts = facts.filter((f) => f.concept === conceptId)
  if (conceptFacts.length === 0) return null

  // Sort periods by end_date descending to find the latest
  const sortedPeriods = [...periods].sort((a, b) => 
    new Date(b.end_date).getTime() - new Date(a.end_date).getTime()
  )

  // Find the latest fact by matching with the latest period
  for (const period of sortedPeriods) {
    const fact = conceptFacts.find((f) => f.fact_period === period.id)
    if (fact) {
      return { fact, period }
    }
  }

  // Fallback: return the first fact with its period
  const firstFact = conceptFacts[0]
  const period = periods.find((p) => p.id === firstFact.fact_period) || null
  return { fact: firstFact, period }
}

export default async function StockPage({ params }: PageProps) {
  const { ticker } = params
  const tickerUpper = ticker.toUpperCase()

  let companyFacts: CompanyFactsResponse | null = null
  let error: string | null = null

  try {
    companyFacts = await fetchFinancialData(tickerUpper)
  } catch (err) {
    error = err instanceof Error ? err.message : "Failed to fetch financial data"
  }

  if (error || !companyFacts) {
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

  const { company, concepts, periods, facts } = companyFacts

  // Get the latest period for display
  const latestPeriod = periods.length > 0
    ? [...periods].sort((a, b) => 
        new Date(b.end_date).getTime() - new Date(a.end_date).getTime()
      )[0]
    : null

  return (
    <div className="container mx-auto p-8">
      <h1 className="text-4xl font-bold mb-2">{company.name || tickerUpper}</h1>
      {company.ticker && (
        <p className="text-muted-foreground mb-2">Ticker: {company.ticker}</p>
      )}
      {latestPeriod && (
        <p className="text-muted-foreground mb-8">
          Latest Period: {latestPeriod.id} ({latestPeriod.period_type})
        </p>
      )}

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {concepts.map((concept) => {
          const latestFactData = getLatestFactForConcept(concept.id, facts, periods)
          
          if (!latestFactData) {
            return null
          }

          const { fact, period } = latestFactData
          const formattedValue = formatValue(fact.value, concept.unit)

          return (
            <Card key={concept.id}>
              <CardHeader>
                <CardTitle>{concept.label}</CardTitle>
                <CardDescription>
                  {period ? `Period: ${period.id}` : concept.tag}
                  {concept.unit && ` • Unit: ${concept.unit}`}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold">{formattedValue}</p>
              </CardContent>
            </Card>
          )
        })}
      </div>
    </div>
  )
}
