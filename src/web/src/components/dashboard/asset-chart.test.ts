import { describe, expect, it } from "vitest"
import type { PortfolioHistoryItem } from "@/lib/api/types"
import { filterDataByTimeFrame } from "./asset-chart"

describe("filterDataByTimeFrame", () => {
  const testData: PortfolioHistoryItem[] = [
    {
      date: "2024-01-01",
      total_cost: 1000000,
      total_market_value: 1100000,
      total_unrealized_pl: 100000,
      total_unrealized_pl_percentage: 10,
      total_realized_pl: 0,
      total_dividend: 50000,
      total_pl: 150000,
      total_pl_percentage: 15,
    },
    {
      date: "2024-01-15",
      total_cost: 1050000,
      total_market_value: 1150000,
      total_unrealized_pl: 100000,
      total_unrealized_pl_percentage: 9.5,
      total_realized_pl: 0,
      total_dividend: 55000,
      total_pl: 155000,
      total_pl_percentage: 14.8,
    },
    {
      date: "2024-02-01",
      total_cost: 1100000,
      total_market_value: 1200000,
      total_unrealized_pl: 100000,
      total_unrealized_pl_percentage: 9.1,
      total_realized_pl: 0,
      total_dividend: 60000,
      total_pl: 160000,
      total_pl_percentage: 14.5,
    },
    {
      date: "2024-02-15",
      total_cost: 1150000,
      total_market_value: 1250000,
      total_unrealized_pl: 100000,
      total_unrealized_pl_percentage: 8.7,
      total_realized_pl: 0,
      total_dividend: 65000,
      total_pl: 165000,
      total_pl_percentage: 14.3,
    },
    {
      date: "2025-01-01",
      total_cost: 1200000,
      total_market_value: 1300000,
      total_unrealized_pl: 100000,
      total_unrealized_pl_percentage: 8.3,
      total_realized_pl: 0,
      total_dividend: 70000,
      total_pl: 170000,
      total_pl_percentage: 14.2,
    },
  ]

  it("dailyで全てのデータを返す", () => {
    const result = filterDataByTimeFrame(testData, "daily")
    expect(result).toHaveLength(5)
    expect(result).toEqual(testData)
  })

  it("monthlyで月ごとの最後のデータポイントを抽出できる", () => {
    const result = filterDataByTimeFrame(testData, "monthly")
    // 2024年1月、2024年2月、2025年1月の3つの月があるため、3件のデータが返される
    expect(result).toHaveLength(3)

    // 各月の最後のエントリが含まれることを確認
    // Map.set()は同じキーで上書きするため、各月の最後のデータが残る
    const dates = result.map((item) => item.date)
    expect(dates).toContain("2024-01-15")
    expect(dates).toContain("2024-02-15")
    expect(dates).toContain("2025-01-01")
  })

  it("yearlyで年ごとの最後のデータポイントを抽出できる", () => {
    const result = filterDataByTimeFrame(testData, "yearly")
    // 2024年と2025年の2つの年があるため、2件のデータが返される
    expect(result).toHaveLength(2)

    // 各年の最後のエントリが含まれることを確認
    const dates = result.map((item) => item.date)
    expect(dates).toContain("2024-02-15")
    expect(dates).toContain("2025-01-01")
  })

  it("空配列が渡された場合に空配列を返す", () => {
    const result = filterDataByTimeFrame([], "monthly")
    expect(result).toEqual([])
  })
})
