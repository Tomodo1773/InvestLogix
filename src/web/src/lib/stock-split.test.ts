import { describe, expect, it } from "vitest"
import { formatSplitRatio, splitRatioFromShares } from "./stock-split"

describe("formatSplitRatio", () => {
  it("1より大きい比率を分割として表示する", () => {
    expect(formatSplitRatio(4)).toBe("4:1 分割")
    expect(formatSplitRatio(20)).toBe("20:1 分割")
    expect(formatSplitRatio(1.5)).toBe("1.5:1 分割")
  })

  it("1より小さい比率を併合として表示する", () => {
    expect(formatSplitRatio(0.5)).toBe("1:2 併合")
    expect(formatSplitRatio(0.2)).toBe("1:5 併合")
  })

  it("浮動小数点の誤差を丸めて表示する", () => {
    // 3株 → 1株の併合。1 / (1/3) が 2.9999... になっても 3 と表示する
    expect(formatSplitRatio(1 / 3)).toBe("1:3 併合")
  })

  it("比率が不正な場合はハイフンを表示する", () => {
    expect(formatSplitRatio(0)).toBe("-")
    expect(formatSplitRatio(-2)).toBe("-")
    expect(formatSplitRatio(Number.NaN)).toBe("-")
  })
})

describe("splitRatioFromShares", () => {
  it("分割前後の株数から比率を求める", () => {
    expect(splitRatioFromShares(1, 4)).toBe(4)
    expect(splitRatioFromShares(2, 3)).toBe(1.5)
  })

  it("併合の比率を求める", () => {
    expect(splitRatioFromShares(2, 1)).toBe(0.5)
  })

  it("株数が正の数でない場合はnullを返す", () => {
    expect(splitRatioFromShares(0, 4)).toBeNull()
    expect(splitRatioFromShares(1, 0)).toBeNull()
    expect(splitRatioFromShares(-1, 4)).toBeNull()
    expect(splitRatioFromShares(Number.NaN, 4)).toBeNull()
  })
})
