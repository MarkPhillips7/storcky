import { describe, it, expect } from "vitest"
import { cn } from "./utils"

describe("cn", () => {
  it("merges class names", () => {
    expect(cn("foo", "bar")).toBe("foo bar")
  })

  it("handles conditional classes with clsx", () => {
    expect(cn("base", false && "hidden", true && "visible")).toBe("base visible")
  })

  it("merges Tailwind classes with twMerge", () => {
    expect(cn("px-2 py-1", "px-4")).toBe("py-1 px-4")
  })
})
