import { render, screen } from "@testing-library/react"
import { MemoryRouter } from "react-router"
import { describe, expect, it } from "vitest"
import type { StockWeeklyPerformance } from "@/lib/api/types"
import { WeeklyPerformanceCard } from "./weekly-performance-card"

function renderWithRouter(ui: React.ReactElement) {
  return render(<MemoryRouter>{ui}</MemoryRouter>)
}

const mockTopPerformers: StockWeeklyPerformance[] = [
  { symbol: "7203", name: "トヨタ自動車", latest_price: 3300, old_price: 3000, change_rate: 10.0 },
  { symbol: "8058", name: "三菱商事", latest_price: 3100, old_price: 3000, change_rate: 3.33 },
]

const mockBottomPerformers: StockWeeklyPerformance[] = [
  { symbol: "7974", name: "任天堂", latest_price: 6500, old_price: 7000, change_rate: -7.14 },
]

describe("WeeklyPerformanceCard", () => {
  it("direction=top のとき値上がりタイトルと銘柄リストが表示されること", () => {
    renderWithRouter(
      <WeeklyPerformanceCard performers={mockTopPerformers} direction="top" isLoading={false} />
    )

    expect(screen.getByText("今週の値上がりトップ5")).toBeInTheDocument()
    expect(screen.getByText("トヨタ自動車")).toBeInTheDocument()
    expect(screen.getByText("7203")).toBeInTheDocument()
    expect(screen.getByText("+10.0%")).toBeInTheDocument()
    expect(screen.getByText("三菱商事")).toBeInTheDocument()
  })

  it("銘柄名が各銘柄の詳細ページへのリンクになっていること", () => {
    renderWithRouter(
      <WeeklyPerformanceCard performers={mockTopPerformers} direction="top" isLoading={false} />
    )

    const toyotaLink = screen.getByText("トヨタ自動車").closest("a")
    expect(toyotaLink).toHaveAttribute("href", "/holdings/7203")
    const mitsubishiLink = screen.getByText("三菱商事").closest("a")
    expect(mitsubishiLink).toHaveAttribute("href", "/holdings/8058")
  })

  it("direction=bottom のとき値下がりタイトルと負の騰落率が表示されること", () => {
    renderWithRouter(
      <WeeklyPerformanceCard performers={mockBottomPerformers} direction="bottom" isLoading={false} />
    )

    expect(screen.getByText("今週の値下がりトップ5")).toBeInTheDocument()
    expect(screen.getByText("任天堂")).toBeInTheDocument()
    expect(screen.getByText("-7.1%")).toBeInTheDocument()
  })

  it("performersが空配列のときフォールバック文言が表示されること", () => {
    renderWithRouter(<WeeklyPerformanceCard performers={[]} direction="top" isLoading={false} />)

    expect(screen.getByText("表示できる銘柄がありません")).toBeInTheDocument()
  })

  it("ローディング中にスケルトンが表示されること", () => {
    renderWithRouter(<WeeklyPerformanceCard performers={undefined} direction="top" isLoading={true} />)

    expect(screen.getByText("今週の値上がりトップ5")).toBeInTheDocument()
    const skeleton = screen.getByText("今週の値上がりトップ5").closest("div")?.parentElement
      ?.nextElementSibling?.firstElementChild
    expect(skeleton).toHaveClass("animate-pulse")
  })
})
