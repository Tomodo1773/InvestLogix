import { render, screen } from "@testing-library/react"
import { MemoryRouter } from "react-router"
import { describe, expect, it } from "vitest"
import type { Holding } from "@/lib/api/types"
import { flattenColorValues, SectorTreemap, transformHoldingsToTreemap } from "./sector-treemap"

const createHolding = (overrides: Partial<Holding>): Holding => ({
  symbol: "TEST",
  quantity: 100,
  average_cost: 1000,
  total_cost: 100000,
  current_price: 1100,
  market_value: 110000,
  realized_pl: 0,
  total_dividend: 0,
  unrealized_pl: 10000,
  unrealized_pl_percentage: 10,
  total_pl: 10000,
  total_pl_percentage: 10,
  user_id: 1,
  last_updated: "2024-01-01",
  stock_name: "テスト",
  security_type: "STOCK",
  currency: "JPY",
  country: "JP",
  sector_name: "情報・通信業",
  note: null,
  ...overrides,
})

describe("transformHoldingsToTreemap", () => {
  it("空配列を渡すと空配列を返す", () => {
    expect(transformHoldingsToTreemap([], { country: "ALL", securityType: "ALL" })).toEqual([])
    expect(transformHoldingsToTreemap(undefined, { country: "ALL", securityType: "ALL" })).toEqual([])
  })

  it("国 → セクター → 銘柄の3階層構造に集約される", () => {
    const holdings: Holding[] = [
      createHolding({
        symbol: "8058",
        stock_name: "三菱商事",
        country: "JP",
        sector_name: "商社・卸売",
        market_value: 300000,
      }),
      createHolding({
        symbol: "7203",
        stock_name: "トヨタ",
        country: "JP",
        sector_name: "自動車・輸送機",
        market_value: 200000,
      }),
      createHolding({
        symbol: "AAPL",
        stock_name: "Apple",
        country: "US",
        sector_name: "Information Technology",
        currency: "USD",
        market_value: 800000,
      }),
    ]
    const result = transformHoldingsToTreemap(holdings, { country: "ALL", securityType: "ALL" })

    // 評価額降順なので US が先
    expect(result).toHaveLength(2)
    expect(result[0].name).toBe("米国")
    expect(result[1].name).toBe("日本")
    // JP の中に 2 セクター
    expect(result[1].children).toHaveLength(2)
  })

  it("country が null の銘柄は OTHER に集約される", () => {
    const holdings: Holding[] = [
      createHolding({ symbol: "X1", country: null, sector_name: null, market_value: 100000 }),
    ]
    const result = transformHoldingsToTreemap(holdings, { country: "ALL", securityType: "ALL" })
    expect(result).toHaveLength(1)
    expect(result[0].name).toBe("その他")
    expect(result[0].children[0].name).toBe("その他")
  })

  it("market_value が 0 以下の銘柄は除外される", () => {
    const holdings: Holding[] = [
      createHolding({ symbol: "ZERO", market_value: 0 }),
      createHolding({ symbol: "NEG", market_value: -100 }),
      createHolding({ symbol: "NULL", market_value: null }),
      createHolding({ symbol: "OK", market_value: 100000 }),
    ]
    const result = transformHoldingsToTreemap(holdings, { country: "ALL", securityType: "ALL" })
    const leaves = result.flatMap((c) => c.children.flatMap((s) => s.children))
    expect(leaves).toHaveLength(1)
  })

  it("国フィルタが効く", () => {
    const holdings: Holding[] = [
      createHolding({ symbol: "JP1", country: "JP" }),
      createHolding({ symbol: "US1", country: "US" }),
    ]
    const result = transformHoldingsToTreemap(holdings, { country: "JP", securityType: "ALL" })
    expect(result).toHaveLength(1)
    expect(result[0].name).toBe("日本")
  })

  it("証券種別フィルタが効く", () => {
    const holdings: Holding[] = [
      createHolding({ symbol: "S", security_type: "STOCK" }),
      createHolding({ symbol: "E", security_type: "ETF" }),
    ]
    const result = transformHoldingsToTreemap(holdings, { country: "ALL", securityType: "ETF" })
    const leaves = result.flatMap((c) => c.children.flatMap((s) => s.children))
    expect(leaves).toHaveLength(1)
    expect(leaves[0].symbol).toBe("E")
  })

  it("セクター内の銘柄が評価額降順でソートされる", () => {
    const holdings: Holding[] = [
      createHolding({ symbol: "SMALL", market_value: 100000, sector_name: "情報・通信業" }),
      createHolding({ symbol: "LARGE", market_value: 500000, sector_name: "情報・通信業" }),
      createHolding({ symbol: "MID", market_value: 300000, sector_name: "情報・通信業" }),
    ]
    const result = transformHoldingsToTreemap(holdings, { country: "ALL", securityType: "ALL" })
    const leaves = result[0].children[0].children
    expect(leaves.map((l) => l.symbol)).toEqual(["LARGE", "MID", "SMALL"])
  })
})

describe("flattenColorValues", () => {
  it("葉のplPercentageを平らに取り出す", () => {
    const holdings: Holding[] = [
      createHolding({ symbol: "A", unrealized_pl_percentage: 10 }),
      createHolding({ symbol: "B", unrealized_pl_percentage: -5, country: "US", sector_name: "X" }),
    ]
    const data = transformHoldingsToTreemap(holdings, { country: "ALL", securityType: "ALL" })
    const values = flattenColorValues(data)
    expect(values.sort()).toEqual([-5, 10])
  })
})

describe("SectorTreemap (rendering)", () => {
  function renderWithRouter(ui: React.ReactElement) {
    return render(<MemoryRouter>{ui}</MemoryRouter>)
  }

  it("ローディング中はスケルトンを表示する", () => {
    renderWithRouter(<SectorTreemap data={undefined} isLoading={true} />)
    expect(screen.getByText("セクター別ツリーマップ")).toBeInTheDocument()
  })

  it("データが無いときに「データがありません」を表示する", () => {
    renderWithRouter(<SectorTreemap data={[]} isLoading={false} />)
    expect(screen.getByText("データがありません")).toBeInTheDocument()
  })

  it("国フィルタボタンが表示される", () => {
    renderWithRouter(<SectorTreemap data={[createHolding({ symbol: "T" })]} isLoading={false} />)
    expect(screen.getByRole("button", { name: "日本" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "米国" })).toBeInTheDocument()
  })
})
