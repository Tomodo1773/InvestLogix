import { render, screen } from "@testing-library/react"
import { userEvent } from "@testing-library/user-event"
import { describe, expect, it } from "vitest"
import type { Stock } from "@/lib/api/types"
import { StocksTable } from "./stocks-table"

const mockStocks: Stock[] = [
  {
    symbol: "7203",
    name: "トヨタ自動車",
    name_en: "Toyota Motor Corporation",
    market: "TSE",
    security_type: "STOCK",
    currency: "JPY",
    last_updated: "2024-01-15T10:30:00+09:00",
  },
  {
    symbol: "AAPL",
    name: "Apple Inc.",
    name_en: "Apple Inc.",
    market: "NASDAQ",
    security_type: "STOCK",
    currency: "USD",
    last_updated: "2024-01-16T10:30:00+09:00",
  },
  {
    symbol: "1306",
    name: "TOPIX連動型上場投資信託",
    name_en: null,
    market: "TSE",
    security_type: "ETF",
    currency: "JPY",
    last_updated: "2024-01-14T10:30:00+09:00",
  },
]

describe("StocksTable", () => {
  it("銘柄データが正しく表示されること", () => {
    render(<StocksTable stocks={mockStocks} isLoading={false} />)

    // シンボル
    expect(screen.getByText("7203")).toBeInTheDocument()
    expect(screen.getByText("AAPL")).toBeInTheDocument()
    expect(screen.getByText("1306")).toBeInTheDocument()

    // 銘柄名
    expect(screen.getByText("トヨタ自動車")).toBeInTheDocument()
    expect(screen.getAllByText("Apple Inc.")).toHaveLength(2) // name と name_en
    expect(screen.getByText("TOPIX連動型上場投資信託")).toBeInTheDocument()

    // 市場
    expect(screen.getAllByText("TSE")).toHaveLength(2)
    expect(screen.getByText("NASDAQ")).toBeInTheDocument()

    // 証券種別（変換後）
    expect(screen.getAllByText("株式")).toHaveLength(2)
    expect(screen.getByText("ETF")).toBeInTheDocument()

    // 通貨
    expect(screen.getAllByText("JPY")).toHaveLength(2)
    expect(screen.getByText("USD")).toBeInTheDocument()
  })

  it("ソート機能が正しく動作すること", async () => {
    const user = userEvent.setup()
    render(<StocksTable stocks={mockStocks} isLoading={false} />)

    // 初期状態はシンボル昇順（1306, 7203, AAPL）
    let rows = screen.getAllByRole("row").slice(1) // ヘッダーを除外
    let cells = rows[0].querySelectorAll("td")
    expect(cells[0]).toHaveTextContent("1306")

    // 銘柄名ヘッダーをクリックして銘柄名で昇順ソート
    const nameHeader = screen.getByText("銘柄名").closest("th")
    if (nameHeader) {
      await user.click(nameHeader)
    }

    // 銘柄名昇順に並び替わる（Apple, TOPIX, トヨタ）
    rows = screen.getAllByRole("row").slice(1)
    cells = rows[0].querySelectorAll("td")
    expect(cells[0]).toHaveTextContent("AAPL") // Apple Inc.が最初
  })

  it("空データ時にメッセージが表示されること", () => {
    render(<StocksTable stocks={[]} isLoading={false} />)

    expect(screen.getByText("登録銘柄がありません")).toBeInTheDocument()
  })

  it("ページネーションが正しく動作すること", async () => {
    const user = userEvent.setup()
    // 25件のデータを作成（ページサイズ20件なので2ページになる）
    // シンボルを0埋めして昇順ソートで順番が保証されるようにする
    const manyStocks: Stock[] = Array.from({ length: 25 }, (_, i) => ({
      symbol: `SYM${String(i + 1).padStart(2, "0")}`,
      name: `株式会社${i + 1}`,
      name_en: `Company ${i + 1}`,
      market: "TSE",
      security_type: "STOCK" as const,
      currency: "JPY",
      last_updated: "2024-01-15T10:30:00+09:00",
    }))

    render(<StocksTable stocks={manyStocks} isLoading={false} />)

    // 1ページ目には20件表示される（初期ソートはsymbol昇順）
    expect(screen.getByText("SYM01")).toBeInTheDocument()
    expect(screen.getByText("SYM20")).toBeInTheDocument()
    expect(screen.queryByText("SYM21")).not.toBeInTheDocument()

    // ページ情報が表示される
    expect(screen.getByText(/25 件中 1 - 20 件を表示/)).toBeInTheDocument()
    expect(screen.getByText("1 / 2")).toBeInTheDocument()

    // 次へボタンをクリック
    const nextButton = screen.getByRole("button", { name: "次へ" })
    await user.click(nextButton)

    // 2ページ目には5件表示される
    expect(screen.getByText("SYM21")).toBeInTheDocument()
    expect(screen.getByText("SYM25")).toBeInTheDocument()
    expect(screen.queryByText("SYM01")).not.toBeInTheDocument()

    // ページ情報が更新される
    expect(screen.getByText(/25 件中 21 - 25 件を表示/)).toBeInTheDocument()
    expect(screen.getByText("2 / 2")).toBeInTheDocument()

    // 前へボタンをクリック
    const prevButton = screen.getByRole("button", { name: "前へ" })
    await user.click(prevButton)

    // 1ページ目に戻る
    expect(screen.getByText("SYM01")).toBeInTheDocument()
    expect(screen.getByText("SYM20")).toBeInTheDocument()
  })

  it("name_enがnullの場合にハイフンが表示されること", () => {
    render(<StocksTable stocks={mockStocks} isLoading={false} />)

    // 1306のname_enはnullなので "-" が表示される
    const rows = screen.getAllByRole("row")
    const etfRow = rows.find((row) => row.textContent?.includes("TOPIX連動型上場投資信託"))
    expect(etfRow).toHaveTextContent("-")
  })
})
