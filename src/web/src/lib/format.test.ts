import { describe, expect, it } from "vitest"
import {
  formatCurrency,
  formatCurrencyWithDecimals,
  formatDate,
  formatPercent,
  formatPercentOrDash,
  formatYearMonth,
} from "./format"

describe("formatCurrency", () => {
  it("正の数を正しくフォーマットできる (JPY)", () => {
    expect(formatCurrency(1234.5, "JPY")).toBe("￥1,235")
  })

  it("正の数を正しくフォーマットできる (USD)", () => {
    expect(formatCurrency(1234.5, "USD")).toBe("$1,235")
  })

  it("負の数を正しくフォーマットできる", () => {
    expect(formatCurrency(-1234.5, "JPY")).toBe("-￥1,235")
  })

  it("文字列の数値を正しく処理できる", () => {
    expect(formatCurrency("1234.5", "JPY")).toBe("￥1,235")
  })

  it("NaNの場合は0を返す", () => {
    expect(formatCurrency(Number.NaN, "JPY")).toBe("￥0")
  })

  it("JPYとUSDで小数点以下の桁数が0であること", () => {
    expect(formatCurrency(1234.89, "JPY")).toBe("￥1,235")
    expect(formatCurrency(1234.89, "USD")).toBe("$1,235")
  })
})

describe("formatCurrencyWithDecimals", () => {
  it("小数点以下2桁でフォーマットできる", () => {
    expect(formatCurrencyWithDecimals(1234.5, "USD")).toBe("$1,234.50")
  })

  it("NaNの場合は0.00を返す", () => {
    expect(formatCurrencyWithDecimals(Number.NaN, "USD")).toBe("$0.00")
  })
})

describe("formatPercent", () => {
  it("正の数に+符号が付与される", () => {
    expect(formatPercent(5)).toBe("+5.0%")
  })

  it("負の数は-符号のまま表示される", () => {
    expect(formatPercent(-3.5)).toBe("-3.5%")
  })

  it("文字列の数値を正しく処理できる", () => {
    expect(formatPercent("5.5")).toBe("+5.5%")
  })

  it("nullの場合は0.0%を返す", () => {
    expect(formatPercent(null)).toBe("0.0%")
  })

  it("undefinedの場合は0.0%を返す", () => {
    expect(formatPercent(undefined)).toBe("0.0%")
  })

  it("0の場合も+符号が付与される", () => {
    expect(formatPercent(0)).toBe("+0.0%")
  })
})

describe("formatPercentOrDash", () => {
  it("数値はformatPercentと同じ形式で返す", () => {
    expect(formatPercentOrDash(5)).toBe("+5.0%")
  })

  it("nullishはハイフンで返す", () => {
    expect(formatPercentOrDash(null)).toBe("-")
    expect(formatPercentOrDash(undefined)).toBe("-")
  })
})

describe("formatYearMonth", () => {
  it("年月を正しくフォーマットできる", () => {
    expect(formatYearMonth(2024, 1)).toBe("2024/01")
  })

  it("1桁の月はゼロパディングされる", () => {
    expect(formatYearMonth(2024, 3)).toBe("2024/03")
  })

  it("2桁の月はそのまま表示される", () => {
    expect(formatYearMonth(2024, 12)).toBe("2024/12")
  })
})

describe("formatDate", () => {
  it("ISO形式の日付文字列をYYYY/MM/DD形式に変換できる", () => {
    expect(formatDate("2024-01-15")).toBe("2024/01/15")
  })

  it("タイムスタンプ付き日付を正しく処理できる", () => {
    expect(formatDate("2024-01-15T12:30:00Z")).toBe("2024/01/15")
  })

  it("無効な日付文字列の場合は空文字列を返す", () => {
    expect(formatDate("invalid-date")).toBe("")
  })
})
