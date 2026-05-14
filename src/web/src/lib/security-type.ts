export type SecurityTypeFilter = "ALL" | "STOCK" | "ETF" | "FUND" | "REIT"

export const SECURITY_TYPE_FILTERS: { value: SecurityTypeFilter; label: string }[] = [
  { value: "ALL", label: "すべて" },
  { value: "STOCK", label: "株式" },
  { value: "ETF", label: "ETF" },
  { value: "FUND", label: "投信" },
  { value: "REIT", label: "REIT" },
]
