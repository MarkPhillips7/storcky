import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { CompanyFact, CompanyFactsResponse, Concept, FactPeriod, fetchFinancialData } from '@/lib/api';

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
  conceptTag: string,
  periods: FactPeriod[]
): { fact: CompanyFact; period: FactPeriod | null } | null {
  // Sort periods by end_date descending to find the latest
  const sortedPeriods = [...periods].sort((a, b) => 
    new Date(b.end_date).getTime() - new Date(a.end_date).getTime()
  )

  // Find the latest fact for this concept by checking each period's facts
  for (const period of sortedPeriods) {
    const fact = period.facts.find((f) => f.concept === conceptTag)
    if (fact) {
      return { fact, period }
    }
  }

  return null
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

  const { company, concepts, periods } = companyFacts

  // Get the latest period for display
  const latestPeriod = periods && periods.length > 0
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
          const latestFactData = getLatestFactForConcept(concept.tag, periods)
          
          if (!latestFactData) {
            return null
          }

          const { fact, period } = latestFactData
          const formattedValue = formatValue(fact.value, concept.unit)

          return (
            <Card key={concept.tag}>
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
