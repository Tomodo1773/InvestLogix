import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"
import type { StockSplit } from "@/lib/api/types"
import { StockSplitsTable } from "./stock-splits-table"

const mockStockSplits: StockSplit[] = [
  {
    split_id: 1,
    user_id: 1,
    symbol: "AAPL",
    split_date: "2024-06-10",
    split_ratio: 4.0,
    created_at: "2024-06-11T10:00:00+09:00",
    stock_name: "Apple Inc.",
  },
  {
    split_id: 2,
    user_id: 1,
    symbol: "TSLA",
    split_date: "2022-08-25",
    split_ratio: 3.0,
    created_at: "2022-08-26T10:00:00+09:00",
    stock_name: "Tesla, Inc.",
  },
  {
    split_id: 3,
    user_id: 1,
    symbol: "GOOGL",
    split_date: "2022-07-15",
    split_ratio: 20.0,
    created_at: "2022-07-16T10:00:00+09:00",
    stock_name: "Alphabet Inc.",
  },
]

describe("StockSplitsTable", () => {
  it("株式分割データが正しく表示されること", () => {
    render(<StockSplitsTable stockSplits={mockStockSplits} isLoading={false} />)

    // シンボル
    expect(screen.getByText("AAPL")).toBeInTheDocument()
    expect(screen.getByText("TSLA")).toBeInTheDocument()
    expect(screen.getByText("GOOGL")).toBeInTheDocument()

    // 銘柄名
    expect(screen.getByText("Apple Inc.")).toBeInTheDocument()
    expect(screen.getByText("Tesla, Inc.")).toBeInTheDocument()
    expect(screen.getByText("Alphabet Inc.")).toBeInTheDocument()

    // 分割日
    expect(screen.getByText("2024/06/10")).toBeInTheDocument()
    expect(screen.getByText("2022/08/25")).toBeInTheDocument()
    expect(screen.getByText("2022/07/15")).toBeInTheDocument()

    // 分割比率（フォーマット後）
    expect(screen.getByText("4:1 分割")).toBeInTheDocument()
    expect(screen.getByText("3:1 分割")).toBeInTheDocument()
    expect(screen.getByText("20:1 分割")).toBeInTheDocument()
  })

  it("ソート機能が正しく動作すること", () => {
    render(<StockSplitsTable stockSplits={mockStockSplits} isLoading={false} />)

    // 初期状態は分割日の降順（2024/06/10が最初）
    const rows = screen.getAllByRole("row").slice(1) // ヘッダーを除外
    const cells = rows[0].querySelectorAll("td")
    expect(cells[0]).toHaveTextContent("2024/06/10")
    expect(cells[1]).toHaveTextContent("AAPL")

    // ソートヘッダーがクリック可能であることを確認
    const symbolHeader = screen.getByText("銘柄コード").closest("th")
    expect(symbolHeader).toHaveClass("cursor-pointer")
  })

  it("空データ時にメッセージが表示されること", () => {
    render(<StockSplitsTable stockSplits={[]} isLoading={false} />)

    expect(screen.getByText("株式分割履歴がありません")).toBeInTheDocument()
  })

  it("ページネーションが正しく動作すること", () => {
    // 25件のデータを作成（ページサイズ20件なので2ページになる）
    const manyStockSplits: StockSplit[] = Array.from({ length: 25 }, (_, i) => ({
      split_id: i + 1,
      user_id: 1,
      symbol: `SYM${String(i + 1).padStart(2, "0")}`,
      split_date: `2024-01-${String((i % 28) + 1).padStart(2, "0")}`,
      split_ratio: 2.0,
      created_at: `2024-01-${String((i % 28) + 1).padStart(2, "0")}T10:00:00+09:00`,
      stock_name: `Stock ${i + 1}`,
    }))

    render(<StockSplitsTable stockSplits={manyStockSplits} isLoading={false} />)

    // 1ページ目には20件表示される
    const firstPageRows = screen.getAllByRole("row").slice(1)
    expect(firstPageRows).toHaveLength(20)
  })
})
