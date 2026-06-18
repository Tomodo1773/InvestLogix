import { describe, expect, it } from "vitest"
import type { DividendBySymbolItem } from "@/lib/api/types"
import { transformDividendsToChartData } from "./dividend-allocation-chart"

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
    // 大口2件 + 小口3件（それぞれ全体の1%未満）
    const data: DividendBySymbolItem[] = [
      createItem("BIG1", 50000),
      createItem("BIG2", 49000),
      createItem("SMALL1", 5), // 全体(約99060)の0.005%
      createItem("SMALL2", 30),
      createItem("SMALL3", 25),
    ]

    const result = transformDividendsToChartData(data)

    // 大口2件 + その他 = 3件
    expect(result).toHaveLength(3)
    const other = result[result.length - 1]
    expect(other.symbol).toBe("OTHER")
    expect(other.name).toBe("その他")
    // 5 + 30 + 25 = 60
    expect(other.value).toBe(60)
  })

  it("すべての銘柄が1%以上なら「その他」は追加されない", () => {
    const data: DividendBySymbolItem[] = [createItem("A", 4000), createItem("B", 3000), createItem("C", 3000)]

    const result = transformDividendsToChartData(data)

    expect(result).toHaveLength(3)
    expect(result.every((item) => item.symbol !== "OTHER")).toBe(true)
  })

  it("件数が多くても1%以上の銘柄はすべて個別表示する", () => {
    // 均等な50銘柄（各2% > 1%）はすべて個別表示される
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
