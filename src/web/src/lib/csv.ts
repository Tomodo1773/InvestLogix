import type { Holding } from "./api/types"

const CSV_HEADERS = [
  "銘柄コード",
  "銘柄名",
  "株数",
  "評価額",
  "含み損益",
  "含み損益率",
  "実現損益",
  "受取配当金",
  "合計損益",
  "合計損益率",
  "最終更新日時",
  "メモ",
] as const

export function escapeCsvField(value: string | number | null | undefined): string {
  if (value === null || value === undefined) return ""
  const str = String(value)
  if (/[",\r\n]/.test(str)) {
    return `"${str.replace(/"/g, '""')}"`
  }
  return str
}

function roundNumeric(value: number | null | undefined, digits: number): string {
  if (value === null || value === undefined) return ""
  return Number(value.toFixed(digits)).toString()
}

function stripMicroseconds(isoDate: string | null | undefined): string {
  if (!isoDate) return ""
  return isoDate.replace(/\.\d+(?=[+\-Z])/, "")
}

export function holdingsToCsv(holdings: Holding[]): string {
  const rows = holdings.map((h) =>
    [
      h.symbol,
      h.stock_name,
      roundNumeric(h.quantity, 4),
      roundNumeric(h.market_value, 2),
      roundNumeric(h.unrealized_pl, 2),
      roundNumeric(h.unrealized_pl_percentage, 2),
      roundNumeric(h.realized_pl, 2),
      roundNumeric(h.total_dividend, 2),
      roundNumeric(h.total_pl, 2),
      roundNumeric(h.total_pl_percentage, 2),
      stripMicroseconds(h.last_updated),
      h.note,
    ]
      .map(escapeCsvField)
      .join(",")
  )

  const lines = [CSV_HEADERS.join(","), ...rows]
  return `﻿${lines.join("\r\n")}`
}

export function downloadCsv(filename: string, csv: string): void {
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" })
  const url = URL.createObjectURL(blob)
  const link = document.createElement("a")
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}
