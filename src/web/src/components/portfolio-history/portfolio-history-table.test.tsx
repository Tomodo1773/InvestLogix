import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"
import type { PortfolioHistoryItem } from "@/lib/api/types"
import { PortfolioHistoryTable } from "./portfolio-history-table"

const mockHistory: PortfolioHistoryItem[] = [
  {
    date: "2024-01-15",
    total_cost: 1000000,
    total_market_value: 1100000,
    total_unrealized_pl: 100000,
    total_unrealized_pl_percentage: 10.0,
    total_realized_pl: 50000,
    total_dividend: 20000,
    total_pl: 170000,
    total_pl_percentage: 17.0,
  },
  {
    date: "2024-01-16",
    total_cost: 1000000,
    total_market_value: 950000,
    total_unrealized_pl: -50000,
    total_unrealized_pl_percentage: -5.0,
    total_realized_pl: 50000,
    total_dividend: 20000,
    total_pl: 20000,
    total_pl_percentage: 2.0,
  },
  {
    date: "2024-01-17",
    total_cost: 1000000,
    total_market_value: 1000000,
    total_unrealized_pl: 0,
    total_unrealized_pl_percentage: 0.0,
    total_realized_pl: 50000,
    total_dividend: 20000,
    total_pl: 70000,
    total_pl_percentage: 7.0,
  },
]

describe("PortfolioHistoryTable", () => {
  it("履歴データが正しく表示されること", () => {
    render(<PortfolioHistoryTable history={mockHistory} isLoading={false} />)

    // 日付
    expect(screen.getByText("2024/01/15")).toBeInTheDocument()
    expect(screen.getByText("2024/01/16")).toBeInTheDocument()
    expect(screen.getByText("2024/01/17")).toBeInTheDocument()

    // データが3行表示されること
    const rows = screen.getAllByRole("row")
    expect(rows).toHaveLength(4) // ヘッダー1行 + データ3行

    // 評価損益率
    expect(screen.getByText("+10.00%")).toBeInTheDocument()
    expect(screen.getByText("-5.00%")).toBeInTheDocument()
    expect(screen.getByText("+0.00%")).toBeInTheDocument()
  })

  it("初期ソートが日付降順であること", () => {
    render(<PortfolioHistoryTable history={mockHistory} isLoading={false} />)

    // 初期状態は日付降順（2024-01-17, 2024-01-16, 2024-01-15）
    const rows = screen.getAllByRole("row").slice(1) // ヘッダーを除外
    const cells = rows[0].querySelectorAll("td")
    expect(cells[0]).toHaveTextContent("2024/01/17")
  })

  it("評価損益が正・負・ゼロで色分けされること", () => {
    render(<PortfolioHistoryTable history={mockHistory} isLoading={false} />)

    const rows = screen.getAllByRole("row")

    // 2024-01-15（評価損益+10万円）は緑色
    const positiveRow = rows.find((row) => row.textContent?.includes("2024/01/15"))
    const positiveCells = positiveRow?.querySelectorAll("td")
    expect(positiveCells?.[3]).toHaveClass("text-success") // 評価損益

    // 2024-01-16（評価損益-5万円）は赤色
    const negativeRow = rows.find((row) => row.textContent?.includes("2024/01/16"))
    const negativeCells = negativeRow?.querySelectorAll("td")
    expect(negativeCells?.[3]).toHaveClass("text-destructive") // 評価損益
  })

  it("空データ時にメッセージが表示されること", () => {
    render(<PortfolioHistoryTable history={[]} isLoading={false} />)

    expect(screen.getByText("履歴がありません")).toBeInTheDocument()
  })

  it("多数のデータがある場合はページネーションが表示されること", () => {
    // 25件のデータを作成（ページサイズ20件なので2ページになる）
    const manyHistory: PortfolioHistoryItem[] = Array.from({ length: 25 }, (_, i) => ({
      date: `2024-01-${String(i + 1).padStart(2, "0")}`,
      total_cost: 1000000,
      total_market_value: 1100000,
      total_unrealized_pl: 100000,
      total_unrealized_pl_percentage: 10.0,
      total_realized_pl: 50000,
      total_dividend: 20000,
      total_pl: 170000,
      total_pl_percentage: 17.0,
    }))

    render(<PortfolioHistoryTable history={manyHistory} isLoading={false} />)

    // 1ページ目には20件表示される（初期ソートは日付降順）
    expect(screen.getByText("2024/01/25")).toBeInTheDocument()
    expect(screen.getByText("2024/01/06")).toBeInTheDocument()
    expect(screen.queryByText("2024/01/05")).not.toBeInTheDocument()

    // ページネーションが表示されていることを確認
    const rows = screen.getAllByRole("row")
    expect(rows).toHaveLength(21) // ヘッダー1行 + データ20行
  })
})
