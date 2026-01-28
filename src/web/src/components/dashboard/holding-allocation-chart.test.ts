import { describe, expect, it } from "vitest"
import type { Holding } from "@/lib/api/types"
import { transformHoldingsToChartData } from "./holding-allocation-chart"

describe("transformHoldingsToChartData", () => {
  const createHolding = (
    symbol: string,
    marketValue: string,
    stockName: string | null = null,
    securityType: string | null = "STOCK"
  ): Holding => ({
    symbol,
    quantity: "100",
    average_cost: "1000",
    total_cost: "100000",
    current_price: "1100",
    market_value: marketValue,
    realized_pl: "0",
    total_dividend: "0",
    unrealized_pl: "10000",
    total_pl: "10000",
    unrealized_pl_percentage: "10",
    user_id: 1,
    last_updated: "2024-01-01",
    stock_name: stockName,
    security_type: securityType,
    currency: "JPY",
  })

  it("上位20銘柄を個別に表示する", () => {
    const holdings: Holding[] = Array.from({ length: 15 }, (_, i) =>
      createHolding(`STOCK${i + 1}`, ((20 - i) * 100000).toString(), `株式${i + 1}`)
    )

    const result = transformHoldingsToChartData(holdings)

    expect(result).toHaveLength(15)
    expect(result[0].symbol).toBe("STOCK1")
    expect(result[0].value).toBe(2000000)
    expect(result[0].name).toBe("株式1")
  })

  it("21位以降を「その他」として集約する", () => {
    const holdings: Holding[] = Array.from({ length: 25 }, (_, i) =>
      createHolding(`STOCK${i + 1}`, ((30 - i) * 10000).toString(), `株式${i + 1}`)
    )

    const result = transformHoldingsToChartData(holdings)

    // 上位20銘柄 + その他 = 21件
    expect(result).toHaveLength(21)

    // 最後の要素が「その他」であることを確認
    const otherItem = result[result.length - 1]
    expect(otherItem.symbol).toBe("OTHER")
    expect(otherItem.name).toBe("その他")

    // 「その他」の合計値が21位以降の合計と一致することを確認
    // 21位: 100000, 22位: 90000, 23位: 80000, 24位: 70000, 25位: 60000
    // 合計: 400000
    expect(otherItem.value).toBe(400000)
  })

  it("評価額でソートされる（降順）", () => {
    const holdings: Holding[] = [
      createHolding("AAPL", "1000000", "Apple"),
      createHolding("GOOGL", "3000000", "Google"),
      createHolding("MSFT", "2000000", "Microsoft"),
    ]

    const result = transformHoldingsToChartData(holdings)

    expect(result).toHaveLength(3)
    expect(result[0].symbol).toBe("GOOGL")
    expect(result[1].symbol).toBe("MSFT")
    expect(result[2].symbol).toBe("AAPL")
  })

  it("評価額が0または負の銘柄はフィルタリングされる", () => {
    const holdings: Holding[] = [
      createHolding("AAPL", "1000000", "Apple"),
      createHolding("GOOGL", "0", "Google"),
      createHolding("MSFT", "-100000", "Microsoft"),
      createHolding("TSLA", "500000", "Tesla"),
    ]

    const result = transformHoldingsToChartData(holdings)

    expect(result).toHaveLength(2)
    expect(result[0].symbol).toBe("AAPL")
    expect(result[1].symbol).toBe("TSLA")
  })

  it("stock_nameがnullの場合はsymbolを使用する", () => {
    const holdings: Holding[] = [createHolding("AAPL", "1000000", null)]

    const result = transformHoldingsToChartData(holdings)

    expect(result).toHaveLength(1)
    expect(result[0].name).toBe("AAPL")
  })

  it("空配列が渡された場合に空配列を返す", () => {
    const result = transformHoldingsToChartData([])
    expect(result).toEqual([])
  })

  it("undefinedが渡された場合に空配列を返す", () => {
    const result = transformHoldingsToChartData(undefined)
    expect(result).toEqual([])
  })

  it("20銘柄以下の場合は「その他」が追加されない", () => {
    const holdings: Holding[] = Array.from({ length: 10 }, (_, i) =>
      createHolding(`STOCK${i + 1}`, ((20 - i) * 100000).toString(), `株式${i + 1}`)
    )

    const result = transformHoldingsToChartData(holdings)

    // 10銘柄のみ（「その他」なし）
    expect(result).toHaveLength(10)
    expect(result.every((item) => item.symbol !== "OTHER")).toBe(true)
  })

  it("market_valueがnullまたは空文字の場合は0として扱われフィルタリングされる", () => {
    const holdings: Holding[] = [
      createHolding("AAPL", "1000000", "Apple"),
      { ...createHolding("GOOGL", "", "Google"), market_value: null },
      { ...createHolding("MSFT", "", "Microsoft"), market_value: "" },
    ]

    const result = transformHoldingsToChartData(holdings)

    expect(result).toHaveLength(1)
    expect(result[0].symbol).toBe("AAPL")
  })

  describe("フィルタ機能", () => {
    it("フィルタなし（ALL）の場合、すべてのsecurity_typeが表示される", () => {
      const holdings: Holding[] = [
        createHolding("AAPL", "1000000", "Apple", "STOCK"),
        createHolding("VTI", "800000", "Vanguard Total Stock", "ETF"),
        createHolding("REIT1", "600000", "REIT1", "REIT"),
        createHolding("FUND1", "400000", "Fund1", "FUND"),
      ]

      const result = transformHoldingsToChartData(holdings, "ALL")

      expect(result).toHaveLength(4)
      expect(result.map((item) => item.symbol)).toEqual(["AAPL", "VTI", "REIT1", "FUND1"])
    })

    it("STOCKフィルタで株式のみが表示される", () => {
      const holdings: Holding[] = [
        createHolding("AAPL", "1000000", "Apple", "STOCK"),
        createHolding("GOOGL", "900000", "Google", "STOCK"),
        createHolding("VTI", "800000", "Vanguard Total Stock", "ETF"),
        createHolding("REIT1", "600000", "REIT1", "REIT"),
      ]

      const result = transformHoldingsToChartData(holdings, "STOCK")

      expect(result).toHaveLength(2)
      expect(result.map((item) => item.symbol)).toEqual(["AAPL", "GOOGL"])
    })

    it("ETFフィルタでETFのみが表示される", () => {
      const holdings: Holding[] = [
        createHolding("AAPL", "1000000", "Apple", "STOCK"),
        createHolding("VTI", "900000", "Vanguard Total Stock", "ETF"),
        createHolding("VOO", "800000", "Vanguard S&P 500", "ETF"),
        createHolding("REIT1", "600000", "REIT1", "REIT"),
      ]

      const result = transformHoldingsToChartData(holdings, "ETF")

      expect(result).toHaveLength(2)
      expect(result.map((item) => item.symbol)).toEqual(["VTI", "VOO"])
    })

    it("FUNDフィルタで投資信託のみが表示される", () => {
      const holdings: Holding[] = [
        createHolding("AAPL", "1000000", "Apple", "STOCK"),
        createHolding("FUND1", "900000", "Fund1", "FUND"),
        createHolding("FUND2", "800000", "Fund2", "FUND"),
        createHolding("VTI", "700000", "Vanguard Total Stock", "ETF"),
      ]

      const result = transformHoldingsToChartData(holdings, "FUND")

      expect(result).toHaveLength(2)
      expect(result.map((item) => item.symbol)).toEqual(["FUND1", "FUND2"])
    })

    it("REITフィルタでREITのみが表示される", () => {
      const holdings: Holding[] = [
        createHolding("AAPL", "1000000", "Apple", "STOCK"),
        createHolding("REIT1", "900000", "REIT1", "REIT"),
        createHolding("REIT2", "800000", "REIT2", "REIT"),
        createHolding("VTI", "700000", "Vanguard Total Stock", "ETF"),
      ]

      const result = transformHoldingsToChartData(holdings, "REIT")

      expect(result).toHaveLength(2)
      expect(result.map((item) => item.symbol)).toEqual(["REIT1", "REIT2"])
    })

    it("フィルタ適用後も上位20銘柄制限が機能する", () => {
      const holdings: Holding[] = Array.from({ length: 25 }, (_, i) =>
        createHolding(`STOCK${i + 1}`, ((30 - i) * 10000).toString(), `株式${i + 1}`, "STOCK")
      )

      const result = transformHoldingsToChartData(holdings, "STOCK")

      // 上位20銘柄 + その他 = 21件
      expect(result).toHaveLength(21)
      expect(result[result.length - 1].symbol).toBe("OTHER")
    })

    it("フィルタ条件に一致する銘柄がない場合は空配列を返す", () => {
      const holdings: Holding[] = [
        createHolding("AAPL", "1000000", "Apple", "STOCK"),
        createHolding("GOOGL", "900000", "Google", "STOCK"),
      ]

      const result = transformHoldingsToChartData(holdings, "ETF")

      expect(result).toEqual([])
    })

    it("security_typeがnullの銘柄はフィルタで除外される", () => {
      const holdings: Holding[] = [
        createHolding("AAPL", "1000000", "Apple", "STOCK"),
        createHolding("UNKNOWN", "900000", "Unknown", null),
        createHolding("GOOGL", "800000", "Google", "STOCK"),
      ]

      const result = transformHoldingsToChartData(holdings, "STOCK")

      expect(result).toHaveLength(2)
      expect(result.map((item) => item.symbol)).toEqual(["AAPL", "GOOGL"])
    })
  })
})
