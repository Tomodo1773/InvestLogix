import { describe, expect, it } from "vitest"
import type { DividendBySymbolItem, MonthlyDividendItem } from "@/lib/api/types"
import { buildPeriodOptions, transformDividendsToChartData } from "./dividend-allocation-chart"

describe("transformDividendsToChartData", () => {
  const createItem = (symbol: string, total: number, name = symbol): DividendBySymbolItem => ({
    symbol,
    stock_name: name,
    total_dividend: total,
  })

  it("配当額の降順で個別表示する", () => {
    const data: DividendBySymbolItem[] = [
      createItem("AAPL", 1000, "Apple"),
      createItem("8058", 3000, "三菱商事"),
      createItem("MSFT", 2000, "Microsoft"),
    ]

    const result = transformDividendsToChartData(data)

    expect(result).toHaveLength(3)
    expect(result[0].symbol).toBe("8058")
    expect(result[0].value).toBe(3000)
    expect(result[0].name).toBe("三菱商事")
    expect(result[2].symbol).toBe("AAPL")
  })

  it("累計の1%未満の銘柄を「その他」に集約する", () => {
    const data: DividendBySymbolItem[] = [
      createItem("BIG1", 50000),
      createItem("BIG2", 49000),
      createItem("SMALL1", 5),
      createItem("SMALL2", 30),
      createItem("SMALL3", 25),
    ]

    const result = transformDividendsToChartData(data)

    expect(result).toHaveLength(3)
    const other = result[result.length - 1]
    expect(other.symbol).toBe("OTHER")
    expect(other.name).toBe("その他")
    expect(other.value).toBe(60)
  })

  it("すべての銘柄が1%以上なら「その他」は追加されない", () => {
    const data: DividendBySymbolItem[] = [createItem("A", 4000), createItem("B", 3000), createItem("C", 3000)]

    const result = transformDividendsToChartData(data)

    expect(result).toHaveLength(3)
    expect(result.every((item) => item.symbol !== "OTHER")).toBe(true)
  })

  it("件数が多くても1%以上の銘柄はすべて個別表示する", () => {
    const data: DividendBySymbolItem[] = Array.from({ length: 50 }, (_, i) =>
      createItem(`STOCK${i + 1}`, 1000)
    )

    const result = transformDividendsToChartData(data)

    expect(result).toHaveLength(50)
    expect(result.every((item) => item.symbol !== "OTHER")).toBe(true)
  })

  it("配当額が0以下の銘柄はフィルタリングされる", () => {
    const data: DividendBySymbolItem[] = [createItem("A", 1000), createItem("B", 0), createItem("C", -500)]

    const result = transformDividendsToChartData(data)

    expect(result).toHaveLength(1)
    expect(result[0].symbol).toBe("A")
  })

  it("stock_nameが空の場合はsymbolを使用する", () => {
    const data: DividendBySymbolItem[] = [createItem("AAPL", 1000, "")]

    const result = transformDividendsToChartData(data)

    expect(result).toHaveLength(1)
    expect(result[0].name).toBe("AAPL")
  })

  it("空配列が渡された場合に空配列を返す", () => {
    expect(transformDividendsToChartData([])).toEqual([])
  })

  it("undefinedが渡された場合に空配列を返す", () => {
    expect(transformDividendsToChartData(undefined)).toEqual([])
  })
})

describe("buildPeriodOptions", () => {
  it("配当がある月のみを降順で返す", () => {
    const data: MonthlyDividendItem[] = [
      { year: 2024, month: 1, total_dividend: 1000 },
      { year: 2024, month: 2, total_dividend: 0 },
      { year: 2024, month: 3, total_dividend: 500 },
    ]

    const result = buildPeriodOptions(data)

    expect(result).toHaveLength(2)
    expect(result[0]).toEqual({ value: "2024-03", label: "2024年3月" })
    expect(result[1]).toEqual({ value: "2024-01", label: "2024年1月" })
  })

  it("undefinedが渡された場合に空配列を返す", () => {
    expect(buildPeriodOptions(undefined)).toEqual([])
  })

  it("全ての月の配当が0の場合に空配列を返す", () => {
    const data: MonthlyDividendItem[] = [
      { year: 2024, month: 1, total_dividend: 0 },
      { year: 2024, month: 2, total_dividend: 0 },
    ]

    expect(buildPeriodOptions(data)).toEqual([])
  })

  it("年をまたいで降順でソートされる", () => {
    const data: MonthlyDividendItem[] = [
      { year: 2023, month: 12, total_dividend: 100 },
      { year: 2024, month: 6, total_dividend: 200 },
      { year: 2024, month: 1, total_dividend: 300 },
    ]

    const result = buildPeriodOptions(data)

    expect(result).toHaveLength(3)
    expect(result[0].value).toBe("2024-06")
    expect(result[1].value).toBe("2024-01")
    expect(result[2].value).toBe("2023-12")
  })
})
