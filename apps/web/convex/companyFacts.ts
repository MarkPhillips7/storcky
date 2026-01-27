import { query, mutation } from "./_generated/server"
import { v } from "convex/values"

/**
 * Get the most recent company facts for a given ticker.
 * Returns the cached facts data and filingDate, or null if not found.
 */
export const getCompanyFactsByTicker = query({
  args: { ticker: v.string() },
  handler: async (ctx, args) => {
    const { ticker } = args
    
    // Query all records for this ticker
    const records = await ctx.db
      .query("companyFacts")
      .withIndex("by_ticker", (q) => q.eq("ticker", ticker.toUpperCase()))
      .collect()
    
    if (records.length === 0) {
      return null
    }
    
    // Find the most recent record by filingDate (sort in memory)
    const mostRecent = records.reduce((latest, current) => {
      return current.filingDate > latest.filingDate ? current : latest
    })
    
    return {
      facts: mostRecent.facts,
      filingDate: mostRecent.filingDate,
      updatedAt: mostRecent.updatedAt,
    }
  },
})

/**
 * Store company facts data. Always inserts a new record (never updates).
 * This preserves historical data over time.
 */
export const storeCompanyFacts = mutation({
  args: {
    ticker: v.string(),
    facts: v.any(), // JSON blob
    filingDate: v.number(), // timestamp
  },
  handler: async (ctx, args) => {
    const { ticker, facts, filingDate } = args
    
    // Always insert a new record - never update existing ones
    const now = Date.now()
    
    await ctx.db.insert("companyFacts", {
      ticker: ticker.toUpperCase(),
      facts,
      filingDate,
      updatedAt: now,
    })
    
    return { success: true }
  },
})
