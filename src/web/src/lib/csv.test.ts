import { describe, expect, it } from "vitest"
import type { Holding } from "./api/types"
import { escapeCsvField, holdingsToCsv } from "./csv"

const BOM = "﻿"

const baseHolding: Holding = {
  symbol: "7203",
  quantity: 100,
  average_cost: 2000,
  total_cost: 200000,
  current_price: 2500,
  market_value: 250000,
  realized_pl: 1000,
  total_dividend: 500,
  unrealized_pl: 50000,
  unrealized_pl_percentage: 25,
  total_pl: 51500,
  total_pl_percentage: 25.75,
  user_id: 1,
  last_updated: "2026-05-01T10:00:00+09:00",
  stock_name: "トヨタ自動車",
  security_type: "stock",
  currency: "JPY",
  country: null,
  sector_name: null,
  note: null,
}

describe("escapeCsvField", () => {
  it("通常の文字列はそのまま返す", () => {
    expect(escapeCsvField("hello")).toBe("hello")
  })

  it("数値は文字列化して返す", () => {
    expect(escapeCsvField(123.45)).toBe("123.45")
  })

  it("nullは空文字を返す", () => {
    expect(escapeCsvField(null)).toBe("")
  })

  it("undefinedは空文字を返す", () => {
    expect(escapeCsvField(undefined)).toBe("")
  })

  it("カンマを含む値はダブルクォートで囲む", () => {
    expect(escapeCsvField("a,b")).toBe('"a,b"')
  })

  it("改行を含む値はダブルクォートで囲む", () => {
    expect(escapeCsvField("a\nb")).toBe('"a\nb"')
  })

  it("ダブルクォートを含む値はエスケープして囲む", () => {
    expect(escapeCsvField('a"b')).toBe('"a""b"')
  })
})

describe("holdingsToCsv", () => {
  it("BOM始まり・CRLF区切りでヘッダー行を出力する", () => {
    const csv = holdingsToCsv([])
    expect(csv.startsWith(BOM)).toBe(true)
    expect(csv).toBe(
      `${BOM}銘柄コード,銘柄名,株数,評価額,含み損益,含み損益率,実現損益,受取配当金,合計損益,合計損益率,最終更新日時,メモ`
    )
  })

  it("1件の保有データを期待通りの順で出力する", () => {
    const csv = holdingsToCsv([baseHolding])
    const lines = csv.replace(BOM, "").split("\r\n")
    expect(lines).toHaveLength(2)
    expect(lines[1]).toBe(
      "7203,トヨタ自動車,100,250000,50000,25,1000,500,51500,25.75,2026-05-01T10:00:00+09:00,"
    )
  })

  it("損益率は小数点2桁に丸めて出力する", () => {
    const holding: Holding = {
      ...baseHolding,
      unrealized_pl_percentage: 90.51679707632479,
      total_pl_percentage: -47.794392523364486,
    }
    const csv = holdingsToCsv([holding])
    const lines = csv.replace(BOM, "").split("\r\n")
    const fields = lines[1].split(",")
    expect(fields[5]).toBe("90.52")
    expect(fields[9]).toBe("-47.79")
  })

  it("株数は浮動小数点誤差を除き小数4桁までに丸める", () => {
    const holding: Holding = { ...baseHolding, quantity: 50.80600000000001 }
    const csv = holdingsToCsv([holding])
    const fields = csv.replace(BOM, "").split("\r\n")[1].split(",")
    expect(fields[2]).toBe("50.806")
  })

  it("金額は浮動小数点誤差を除き小数2桁までに丸め、末尾ゼロを削除する", () => {
    const holding: Holding = {
      ...baseHolding,
      market_value: 1929510.2680000004,
      unrealized_pl: 727.296600000016,
      total_pl: 16975.6829,
    }
    const csv = holdingsToCsv([holding])
    const fields = csv.replace(BOM, "").split("\r\n")[1].split(",")
    expect(fields[3]).toBe("1929510.27")
    expect(fields[4]).toBe("727.3")
    expect(fields[8]).toBe("16975.68")
  })

  it("最終更新日時のマイクロ秒を削除する", () => {
    const holding: Holding = { ...baseHolding, last_updated: "2026-05-02T07:40:00.882068+09:00" }
    const csv = holdingsToCsv([holding])
    expect(csv).toContain("2026-05-02T07:40:00+09:00")
    expect(csv).not.toContain("882068")
  })

  it("数値フィールドがnullの場合は空文字で出力する", () => {
    const holding: Holding = {
      ...baseHolding,
      market_value: null,
      unrealized_pl: null,
      unrealized_pl_percentage: null,
      total_pl: null,
      total_pl_percentage: null,
      realized_pl: null,
      total_dividend: null,
      stock_name: null,
    }
    const csv = holdingsToCsv([holding])
    const lines = csv.replace(BOM, "").split("\r\n")
    expect(lines[1]).toBe("7203,,100,,,,,,,,2026-05-01T10:00:00+09:00,")
  })

  it("銘柄名にカンマが含まれる場合はエスケープする", () => {
    const holding: Holding = { ...baseHolding, stock_name: "Alphabet, Inc." }
    const csv = holdingsToCsv([holding])
    expect(csv).toContain('"Alphabet, Inc."')
  })

  it("メモに改行・カンマが含まれる場合はエスケープして出力する", () => {
    const holding: Holding = { ...baseHolding, note: "AI戦略\n半導体, 検索" }
    const csv = holdingsToCsv([holding])
    expect(csv).toContain('"AI戦略\n半導体, 検索"')
  })
})
