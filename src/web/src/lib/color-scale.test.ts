import { describe, expect, it } from "vitest"
import { computeColorScale, getColorForValue, percentile } from "./color-scale"

describe("percentile", () => {
  it("空配列では 0 を返す", () => {
    expect(percentile([], 50)).toBe(0)
  })

  it("単一要素ではその値を返す", () => {
    expect(percentile([42], 50)).toBe(42)
    expect(percentile([42], 5)).toBe(42)
  })

  it("線形補間で計算する", () => {
    // [10, 20, 30, 40, 50] の 50 パーセンタイルは中央の 30
    expect(percentile([10, 20, 30, 40, 50], 50)).toBe(30)
    // 25 パーセンタイル: rank = 1.0 -> 20
    expect(percentile([10, 20, 30, 40, 50], 25)).toBe(20)
  })

  it("クランプして 0/100 を超えるパーセンタイルでも端を返す", () => {
    expect(percentile([10, 20, 30], -10)).toBe(10)
    expect(percentile([10, 20, 30], 150)).toBe(30)
  })
})

describe("computeColorScale", () => {
  it("空配列ではメトリクスのデフォルトレンジを返す", () => {
    const scale = computeColorScale([])
    expect(scale.minValue).toBe(-50)
    expect(scale.maxValue).toBe(100)
    expect(scale.centerValue).toBe(0)
    expect(scale.outOfRangeAbove).toBe(0)
    expect(scale.outOfRangeBelow).toBe(0)
  })

  it("null や NaN を除外する", () => {
    const scale = computeColorScale([null, undefined, Number.NaN, 10])
    // 有効値が 1 つだけ -> minValue は center - 5 で確保される
    expect(scale.minValue).toBeLessThanOrEqual(-5)
    expect(scale.maxValue).toBeGreaterThanOrEqual(5)
  })

  it("全プラスの相場でも赤側が縮退しない（片側 5% 以上を保証）", () => {
    const allPositive = [5, 10, 15, 20, 25, 30, 40, 50]
    const scale = computeColorScale(allPositive)
    expect(scale.minValue).toBeLessThanOrEqual(-5)
    expect(scale.maxValue).toBeGreaterThanOrEqual(5)
  })

  it("全マイナスの相場でも緑側が縮退しない", () => {
    const allNegative = [-30, -20, -15, -10, -5, -2]
    const scale = computeColorScale(allNegative)
    expect(scale.minValue).toBeLessThanOrEqual(-5)
    expect(scale.maxValue).toBeGreaterThanOrEqual(5)
  })

  it("ceil を超える外れ値はクリップしてカウントする", () => {
    // P95 が 100% を超えてしまうほど多くの極端値を含むケース
    const values = Array.from({ length: 20 }, (_, i) => (i < 18 ? 10 : 250))
    const scale = computeColorScale(values)
    expect(scale.maxValue).toBeLessThanOrEqual(100)
    expect(scale.outOfRangeAbove).toBeGreaterThanOrEqual(2)
  })

  it("floor を下回る外れ値はクリップしてカウントする", () => {
    const values = Array.from({ length: 20 }, (_, i) => (i < 18 ? -10 : -80))
    const scale = computeColorScale(values)
    expect(scale.minValue).toBeGreaterThanOrEqual(-50)
    expect(scale.outOfRangeBelow).toBeGreaterThanOrEqual(2)
  })
})

describe("getColorForValue", () => {
  const scale = computeColorScale([-30, -20, -10, 0, 10, 20, 30, 50])

  it("null は中立色を返す", () => {
    expect(getColorForValue(null, scale)).toBe("#9CA3AF")
  })

  it("プラス値は緑系を返す", () => {
    const color = getColorForValue(20, scale)
    expect(color).toMatch(/^hsl\(142,/)
  })

  it("マイナス値は赤系を返す", () => {
    const color = getColorForValue(-20, scale)
    expect(color).toMatch(/^hsl\(0,/)
  })

  it("中心値ぴったりでもエラーなく色を返す", () => {
    const color = getColorForValue(0, scale)
    expect(color).toMatch(/^hsl\(142,/)
  })

  it("NaN は中立色を返す", () => {
    expect(getColorForValue(Number.NaN, scale)).toBe("#9CA3AF")
  })
})
