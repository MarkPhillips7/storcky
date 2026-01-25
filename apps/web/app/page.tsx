import Link from "next/link"
import { Button } from "@/components/ui/button"

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24">
      <div className="z-10 max-w-5xl w-full items-center justify-between font-mono text-sm">
        <div className="text-center space-y-8">
          <h1 className="text-6xl font-bold mb-4">
            Storcky
          </h1>
          <p className="text-xl text-muted-foreground mb-8">
            Interactive animations of financial data for stocks
          </p>
          <p className="text-lg mb-8">
            Explore stock stories through interactive visualizations
          </p>
          <div className="flex justify-center gap-4">
            <Button asChild size="lg">
              <Link href="/stocks/TSLA">
                View Tesla (TSLA)
              </Link>
            </Button>
          </div>
        </div>
      </div>
    </main>
  )
}
