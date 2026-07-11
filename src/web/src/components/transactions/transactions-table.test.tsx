import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"
import type { TransactionWithPL } from "@/lib/api/types"
import { TransactionsTable } from "./transactions-table"

const transaction: TransactionWithPL = {
  symbol: "8058",
  transaction_type: "buy",
  quantity: 100,
  price: 1000,
  usd_price: null,
  adjusted_price: 500,
  adjusted_quantity: 200,
  account_type: "NISA(成長投資枠)",
  fee: 10,
  tax: 5,
  realized_pl: null,
  transaction_id: 1,
  user_id: 1,
  transaction_date: "2024-01-01T00:00:00+09:00",
  stock_name: "三菱商事",
  unrealized_pl: 20000,
  unrealized_pl_percentage: 20,
}

describe("TransactionsTable", () => {
  it("取引履歴ページでは共通列と銘柄列を表示する", () => {
    render(<TransactionsTable transactions={[transaction]} isLoading={false} />)

    expect(screen.getByText("銘柄名/コード")).toBeInTheDocument()
    expect(screen.getByText("口座")).toBeInTheDocument()
    expect(screen.getByText("NISA(成長投資枠)")).toBeInTheDocument()
    expect(screen.queryByText("損益率")).not.toBeInTheDocument()

    const cells = screen.getAllByRole("row")[1].querySelectorAll("td")
    expect(cells).toHaveLength(7)
    expect(cells[1]).toHaveTextContent("三菱商事")
    expect(cells[4]).toHaveTextContent("100")
    expect(cells[5]).toHaveTextContent("1,000")
  })

  it("銘柄詳細では口座と詳細列を表示し、株式分割の調整値を使う", () => {
    render(<TransactionsTable transactions={[transaction]} isLoading={false} mode="holding" />)

    expect(screen.queryByText("銘柄名/コード")).not.toBeInTheDocument()
    expect(screen.getByText("口座")).toBeInTheDocument()
    expect(screen.getByText("手数料")).toBeInTheDocument()
    expect(screen.getByText("税金")).toBeInTheDocument()
    expect(screen.getByText("損益率")).toBeInTheDocument()

    const cells = screen.getAllByRole("row")[1].querySelectorAll("td")
    expect(cells).toHaveLength(9)
    expect(cells[2]).toHaveTextContent("NISA(成長投資枠)")
    expect(cells[3]).toHaveTextContent("200")
    expect(cells[4]).toHaveTextContent("500")
    expect(cells[5]).toHaveTextContent("100,000")
    expect(cells[8]).toHaveTextContent("+20.0%")
  })
})
