import { defineSchema, defineTable } from "convex/server"
import { v } from "convex/values"

export default defineSchema({
  companyFacts: defineTable({
    ticker: v.string(),
    facts: v.any(), // JSON blob storing the serialized EntityFacts data
    filingDate: v.number(), // timestamp of the most recent filing date
    updatedAt: v.number(), // timestamp when record was created
  }).index("by_ticker", ["ticker"]),
})
