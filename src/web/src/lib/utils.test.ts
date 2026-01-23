import { describe, expect, it } from "vitest"
import { cn } from "./utils"

describe("cn (classnames結合)", () => {
  it("複数のクラス名を結合できる", () => {
    expect(cn("btn", "primary")).toBe("btn primary")
  })

  it("条件付きクラス名を正しく処理できる", () => {
    expect(cn("btn", false && "disabled", "active")).toBe("btn active")
    expect(cn("btn", true && "enabled")).toBe("btn enabled")
  })

  it("Tailwindの競合するクラスを正しくマージできる", () => {
    expect(cn("p-2", "p-4")).toBe("p-4")
    expect(cn("text-red-500", "text-blue-500")).toBe("text-blue-500")
  })
})
