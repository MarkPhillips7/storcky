"use client"

import { ConvexReactClient } from "@convex-dev/react"
import { ConvexProvider as ConvexProviderBase } from "@convex-dev/react"

const convex = new ConvexReactClient(process.env.NEXT_PUBLIC_CONVEX_URL || "")

export function ConvexProvider({ children }: { children: React.ReactNode }) {
  return <ConvexProviderBase client={convex}>{children}</ConvexProviderBase>
}
