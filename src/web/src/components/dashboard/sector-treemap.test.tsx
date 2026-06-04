import { render, screen } from "@testing-library/react"
import { MemoryRouter } from "react-router"
import { describe, expect, it } from "vitest"
import type { Holding } from "@/lib/api/types"
import { createHolding as createHoldingBase } from "@/test/factories"
import { flattenColorValues, SectorTreemap, transformHoldingsToTreemap } from "./sector-treemap"

const createHolding = (overrides: Partial<Holding> = {}): Holding =>
  createHoldingBase({ country: "JP", sector_name: "情報・通信業", ...overrides })

describe("transformHoldingsToTreemap", () => {
  it("空配列を渡すと空配列を返す", () => {
    expect(transformHoldingsToTreemap([], { country: "ALL", colorMetric: "weekly_change" })).toEqual([])
    expect(transformHoldingsToTreemap(undefined, { country: "ALL", colorMetric: "weekly_change" })).toEqual(
      []
    )
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
    const result = transformHoldingsToTreemap(holdings, { country: "ALL", colorMetric: "weekly_change" })

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
    const result = transformHoldingsToTreemap(holdings, { country: "ALL", colorMetric: "weekly_change" })
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
    const result = transformHoldingsToTreemap(holdings, { country: "ALL", colorMetric: "weekly_change" })
    const leaves = result.flatMap((c) => c.children.flatMap((s) => s.children))
    expect(leaves).toHaveLength(1)
  })

  it("国フィルタが効く", () => {
    const holdings: Holding[] = [
      createHolding({ symbol: "JP1", country: "JP" }),
      createHolding({ symbol: "US1", country: "US" }),
    ]
    const result = transformHoldingsToTreemap(holdings, { country: "JP", colorMetric: "weekly_change" })
    expect(result).toHaveLength(1)
    expect(result[0].name).toBe("日本")
  })

  it("株式以外は除外される", () => {
    const holdings: Holding[] = [
      createHolding({ symbol: "S", security_type: "STOCK" }),
      createHolding({ symbol: "E", security_type: "ETF" }),
      createHolding({ symbol: "F", security_type: "FUND" }),
      createHolding({ symbol: "R", security_type: "REIT" }),
    ]
    const result = transformHoldingsToTreemap(holdings, { country: "ALL", colorMetric: "weekly_change" })
    const leaves = result.flatMap((c) => c.children.flatMap((s) => s.children))
    expect(leaves).toHaveLength(1)
    expect(leaves[0].symbol).toBe("S")
  })

  it("セクター内の銘柄が評価額降順でソートされる", () => {
    const holdings: Holding[] = [
      createHolding({ symbol: "SMALL", market_value: 100000, sector_name: "情報・通信業" }),
      createHolding({ symbol: "LARGE", market_value: 500000, sector_name: "情報・通信業" }),
      createHolding({ symbol: "MID", market_value: 300000, sector_name: "情報・通信業" }),
    ]
    const result = transformHoldingsToTreemap(holdings, { country: "ALL", colorMetric: "weekly_change" })
    const leaves = result[0].children[0].children
    expect(leaves.map((l) => l.symbol)).toEqual(["LARGE", "MID", "SMALL"])
  })

  it("週次騰落率モードではweeklyChangeMapの値を色指標に使う", () => {
    const holdings: Holding[] = [createHolding({ symbol: "A", unrealized_pl_percentage: 10 })]
    const data = transformHoldingsToTreemap(holdings, {
      country: "ALL",
      colorMetric: "weekly_change",
      weeklyChangeMap: new Map([["A", 3.2]]),
    })
    const leaf = data[0].children[0].children[0]

    expect(leaf.colorValue).toBe(3.2)
    expect(leaf.weeklyChangeRate).toBe(3.2)
    expect(leaf.plPercentage).toBe(10)
  })

  it("週次騰落率が無い株式は残し、色指標はnullにする", () => {
    const holdings: Holding[] = [createHolding({ symbol: "A" })]
    const data = transformHoldingsToTreemap(holdings, { country: "ALL", colorMetric: "weekly_change" })
    const leaves = data.flatMap((c) => c.children.flatMap((s) => s.children))

    expect(leaves).toHaveLength(1)
    expect(leaves[0].colorValue).toBeNull()
  })

  it("損益率モードではunrealized_pl_percentageを色指標に使う", () => {
    const holdings: Holding[] = [createHolding({ symbol: "A", unrealized_pl_percentage: -4.5 })]
    const data = transformHoldingsToTreemap(holdings, {
      country: "ALL",
      colorMetric: "unrealized_pl_percentage",
      weeklyChangeMap: new Map([["A", 3.2]]),
    })
    const leaf = data[0].children[0].children[0]

    expect(leaf.colorValue).toBe(-4.5)
  })
})

describe("flattenColorValues", () => {
  it("葉のcolorValueを平らに取り出す", () => {
    const holdings: Holding[] = [
      createHolding({ symbol: "A", unrealized_pl_percentage: 10 }),
      createHolding({ symbol: "B", unrealized_pl_percentage: -5, country: "US", sector_name: "X" }),
    ]
    const data = transformHoldingsToTreemap(holdings, {
      country: "ALL",
      colorMetric: "unrealized_pl_percentage",
    })
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

  it("色指標の切替を表示し、種別フィルタは表示しない", () => {
    renderWithRouter(<SectorTreemap data={[createHolding({ symbol: "T" })]} isLoading={false} />)
    expect(screen.getByText("色:")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "1週間騰落率" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "損益率" })).toBeInTheDocument()
    expect(screen.queryByText("種別:")).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "投信" })).not.toBeInTheDocument()
  })
})
