import { TrendingDown, TrendingUp } from "lucide-react"
import useSWR from "swr"
import { Card, CardContent } from "@/components/ui/card"
import { getPriceHistory } from "@/lib/api/client"
import type { PriceHistoryResponse } from "@/lib/api/types"
import { formatPercent } from "@/lib/format"

type IndexDef = {
  symbol: string
  label: string
  currency: "JPY" | "USD"
}

const INDICES: readonly IndexDef[] = [
  { symbol: "N225", label: "日経平均", currency: "JPY" },
  { symbol: "TOPIX", label: "TOPIX", currency: "JPY" },
  { symbol: "SP500", label: "S&P 500", currency: "USD" },
  { symbol: "NASDAQ", label: "NASDAQ", currency: "USD" },
] as const

function calcWeeklyChange(history: PriceHistoryResponse | undefined): {
  latest: number | null
  changePct: number | null
} {
  if (!history?.data || history.data.length === 0) {
    return { latest: null, changePct: null }
  }
  const latest = history.data[history.data.length - 1].close
  // 5営業日前との比較。データ不足時は最古の値で代用
  const baseIndex = Math.max(0, history.data.length - 1 - 5)
  const base = history.data[baseIndex].close
  if (base === 0) {
    return { latest, changePct: null }
  }
  const changePct = (latest / base - 1) * 100
  return { latest, changePct }
}

function formatIndexValue(value: number | null, currency: "JPY" | "USD"): string {
  if (value === null) return "-"
  const fractionDigits = currency === "JPY" ? 0 : 2
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  }).format(value)
}

function IndexCard({ index }: { index: IndexDef }) {
  const { data, isLoading } = useSWR(`market-index-${index.symbol}`, () =>
    getPriceHistory(index.symbol, "daily", 10)
  )
  const { latest, changePct } = calcWeeklyChange(data)
  const isPositive = changePct !== null && changePct >= 0
  const color =
    changePct === null ? "text-muted-foreground" : isPositive ? "text-[#4CAF50]" : "text-destructive"
  const bgColor = changePct === null ? "bg-muted/30" : isPositive ? "bg-[#4CAF50]/10" : "bg-destructive/10"
  const Icon = isPositive ? TrendingUp : TrendingDown

  return (
    <Card className="py-4">
      <CardContent className="flex items-center gap-4">
        <div className={`flex h-12 w-12 items-center justify-center rounded-lg ${bgColor}`}>
          <Icon className={`h-6 w-6 ${color}`} />
        </div>
        <div className="min-w-0">
          <p className="text-sm text-muted-foreground">{index.label}</p>
          {isLoading ? (
            <div className="h-7 w-24 animate-pulse rounded bg-muted" />
          ) : (
            <>
              <p className="text-xl font-bold">{formatIndexValue(latest, index.currency)}</p>
              <p className={`text-sm font-medium ${color}`}>{formatPercent(changePct)}</p>
            </>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

export function MarketIndicesCards() {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {INDICES.map((index) => (
        <IndexCard key={index.symbol} index={index} />
      ))}
    </div>
  )
}
