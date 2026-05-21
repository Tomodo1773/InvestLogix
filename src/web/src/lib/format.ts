export function formatCurrency(value: number | string, currency: string = "JPY"): string {
  const numValue = typeof value === "string" ? parseFloat(value) : value
  if (Number.isNaN(numValue)) {
    return new Intl.NumberFormat("ja-JP", {
      style: "currency",
      currency,
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(0)
  }
  return new Intl.NumberFormat("ja-JP", {
    style: "currency",
    currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(numValue)
}

export function formatCurrencyWithDecimals(value: number | string, currency: string = "JPY"): string {
  const numValue = typeof value === "string" ? parseFloat(value) : value
  if (Number.isNaN(numValue)) {
    return new Intl.NumberFormat("ja-JP", {
      style: "currency",
      currency,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(0)
  }
  return new Intl.NumberFormat("ja-JP", {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(numValue)
}

export function formatPercent(value: number | string | null | undefined): string {
  if (value === null || value === undefined) {
    return "0.0%"
  }
  const numValue = typeof value === "string" ? parseFloat(value) : value
  if (Number.isNaN(numValue)) {
    return "0.0%"
  }
  return `${numValue >= 0 ? "+" : ""}${numValue.toFixed(1)}%`
}

export function formatYearMonth(year: number, month: number): string {
  return `${year}/${month.toString().padStart(2, "0")}`
}

export function getPLColorClass(value: number | null | undefined): string {
  if (value === null || value === undefined) return ""
  return value >= 0 ? "text-success" : "text-destructive"
}

export function formatDate(dateString: string): string {
  const date = new Date(dateString)
  if (Number.isNaN(date.getTime())) {
    return ""
  }
  return date.toLocaleDateString("ja-JP", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  })
}
