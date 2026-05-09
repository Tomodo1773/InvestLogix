import { render, screen } from "@testing-library/react"
import { SWRConfig } from "swr"
import { describe, expect, it, vi } from "vitest"
import type { PriceHistoryResponse } from "@/lib/api/types"
import { MarketIndicesCards } from "./market-indices-cards"

vi.mock("@/lib/api/client", () => ({
  getPriceHistory: vi.fn(),
}))

import { getPriceHistory } from "@/lib/api/client"

function renderIsolated() {
  return render(
    <SWRConfig value={{ provider: () => new Map() }}>
      <MarketIndicesCards />
    </SWRConfig>
  )
}

function makeHistory(symbol: string, closes: number[]): PriceHistoryResponse {
  return {
    symbol,
    interval: "daily",
    data: closes.map((close, i) => ({
      date: `2026-05-0${i + 1}`,
      open: close,
      high: close,
      low: close,
      close,
      volume: 0,
    })),
  }
}

describe("MarketIndicesCards", () => {
  it("4指数のラベル・最新値・騰落率が表示される", async () => {
    // 6営業日分（末尾と末尾-5要素で計算）
    const responses: Record<string, PriceHistoryResponse> = {
      N225: makeHistory("N225", [37000, 37200, 37500, 37800, 38000, 38500]), // +4.05%
      TOPIX: makeHistory("TOPIX", [2700, 2720, 2730, 2740, 2750, 2700]), // 0.00%
      SP500: makeHistory("SP500", [6000, 5950, 5900, 5850, 5800, 5700]), // -5.00%
      NASDAQ: makeHistory("NASDAQ", [20000, 20100, 20200, 20300, 20400, 20500]), // +2.50%
    }
    vi.mocked(getPriceHistory).mockImplementation(async (symbol: string) => responses[symbol])

    renderIsolated()

    expect(await screen.findByText("日経平均")).toBeInTheDocument()
    expect(screen.getByText("TOPIX")).toBeInTheDocument()
    expect(screen.getByText("S&P 500")).toBeInTheDocument()
    expect(screen.getByText("NASDAQ")).toBeInTheDocument()

    // JPYは整数表示
    expect(await screen.findByText("38,500")).toBeInTheDocument()
    // USDは小数2桁
    expect(await screen.findByText("5,700.00")).toBeInTheDocument()

    // 騰落率
    expect(await screen.findByText("+4.1%")).toBeInTheDocument()
    expect(await screen.findByText("-5.0%")).toBeInTheDocument()
  })

  it("プラスは緑、マイナスは赤のクラスが付く", async () => {
    const responses: Record<string, PriceHistoryResponse> = {
      N225: makeHistory("N225", [100, 101, 102, 103, 104, 110]),
      TOPIX: makeHistory("TOPIX", [100, 101, 102, 103, 104, 110]),
      SP500: makeHistory("SP500", [110, 109, 108, 107, 106, 100]),
      NASDAQ: makeHistory("NASDAQ", [110, 109, 108, 107, 106, 100]),
    }
    vi.mocked(getPriceHistory).mockImplementation(async (symbol: string) => responses[symbol])

    renderIsolated()

    const positive = await screen.findAllByText("+10.0%")
    expect(positive[0]).toHaveClass("text-[#4CAF50]")

    const negative = await screen.findAllByText("-9.1%")
    expect(negative[0]).toHaveClass("text-destructive")
  })
})
