import { render, screen } from "@testing-library/react"
import { userEvent } from "@testing-library/user-event"
import { MemoryRouter } from "react-router"
import { describe, expect, it } from "vitest"
import { createHolding } from "@/test/factories"
import { HoldingsTable } from "./holdings-table"

function renderTable(holdings = [createHolding()]) {
  return render(
    <MemoryRouter>
      <HoldingsTable holdings={holdings} isLoading={false} />
    </MemoryRouter>
  )
}

describe("HoldingsTable", () => {
  it("ジュニアNISA以外の数量を合算して単元ありをアイコンで表示する", () => {
    renderTable([
      createHolding({
        symbol: "8058",
        stock_name: "三菱商事",
        country: "JP",
        security_type: "STOCK",
        account_holdings: [
          { account_type: "NISA(成長投資枠)", quantity: 80 },
          { account_type: "特定", quantity: 20 },
        ],
      }),
    ])

    expect(screen.getByLabelText("単元あり。その他: 100株")).toBeInTheDocument()
  })

  it("ジュニアNISAはその他口座と合算せずに単元判定する", () => {
    renderTable([
      createHolding({
        symbol: "8058",
        stock_name: "三菱商事",
        country: "JP",
        security_type: "STOCK",
        account_holdings: [
          { account_type: "ジュニアNISA", quantity: 50 },
          { account_type: "特定", quantity: 50 },
        ],
      }),
    ])

    expect(screen.getByLabelText("単元未満。ジュニアNISA: 50株 / その他: 50株")).toBeInTheDocument()
  })

  it("単元列で単元ありの日本株を上位に並び替えられる", async () => {
    const user = userEvent.setup()
    renderTable([
      createHolding({
        symbol: "LESS",
        stock_name: "単元未満",
        country: "JP",
        security_type: "STOCK",
        market_value: 300000,
        account_holdings: [{ account_type: "特定", quantity: 99 }],
      }),
      createHolding({
        symbol: "FULL",
        stock_name: "単元あり",
        country: "JP",
        security_type: "STOCK",
        market_value: 200000,
        account_holdings: [
          { account_type: "NISA(成長投資枠)", quantity: 80 },
          { account_type: "特定", quantity: 20 },
        ],
      }),
      createHolding({
        symbol: "AAPL",
        stock_name: "Apple",
        country: "US",
        security_type: "STOCK",
        market_value: 100000,
        account_holdings: [{ account_type: "特定", quantity: 10 }],
      }),
    ])

    await user.click(screen.getByText("単元"))

    const rows = screen.getAllByRole("row").slice(1)
    expect(rows[0]).toHaveTextContent("単元あり")
    expect(rows[1]).toHaveTextContent("単元未満")
    expect(rows[2]).toHaveTextContent("Apple")
  })
})
