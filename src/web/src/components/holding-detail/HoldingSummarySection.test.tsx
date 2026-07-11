import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"
import { createHolding } from "@/test/factories"
import { HoldingSummarySection } from "./HoldingSummarySection"

describe("HoldingSummarySection", () => {
  it("総保有数と口座別保有数を表示する", () => {
    const holding = createHolding({
      quantity: 100,
      account_holdings: [
        { account_type: "NISA(成長投資枠)", quantity: 80 },
        { account_type: "特定", quantity: 20 },
      ],
    })

    render(<HoldingSummarySection holding={holding} isLoading={false} />)

    expect(screen.getByText("口座別保有数")).toBeInTheDocument()
    expect(screen.getByText("100株")).toBeInTheDocument()
    expect(screen.getByText("NISA(成長投資枠)")).toBeInTheDocument()
    expect(screen.getByText("80株")).toBeInTheDocument()
    expect(screen.getByText("特定")).toBeInTheDocument()
    expect(screen.getByText("20株")).toBeInTheDocument()
  })

  it("口座別保有数がない場合は空状態を表示する", () => {
    render(<HoldingSummarySection holding={createHolding()} isLoading={false} />)

    expect(screen.getByText("口座別の保有情報がありません")).toBeInTheDocument()
  })
})
