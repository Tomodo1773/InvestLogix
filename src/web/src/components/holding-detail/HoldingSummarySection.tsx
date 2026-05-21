import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { Holding } from "@/lib/api/types"
import { formatCurrency, formatPercent, getPLColorClass } from "@/lib/format"

interface HoldingSummarySectionProps {
  holding: Holding | undefined
  isLoading: boolean
}

export function HoldingSummarySection({ holding, isLoading }: HoldingSummarySectionProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>保有状況サマリ</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-5">
            {[...Array(5)].map((_, i) => (
              // biome-ignore lint/suspicious/noArrayIndexKey: Static skeleton loading elements
              <div key={`skeleton-${i}`} className="space-y-2">
                <div className="h-4 w-20 animate-pulse rounded bg-muted" />
                <div className="h-6 w-24 animate-pulse rounded bg-muted" />
              </div>
            ))}
          </div>
        ) : holding ? (
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-5">
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">保有数</p>
              <p className="text-lg font-semibold">{holding.quantity.toLocaleString()}株</p>
            </div>
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">平均取得単価</p>
              <p className="text-lg font-semibold">{formatCurrency(holding.average_cost)}</p>
            </div>
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">評価額</p>
              <div className="text-lg font-semibold">
                <p>{holding.market_value ? formatCurrency(holding.market_value, "JPY") : "-"}</p>
                {holding.currency === "USD" ? (
                  <p className="text-sm text-muted-foreground">
                    {holding.market_value_usd ? formatCurrency(holding.market_value_usd, "USD") : "-"}
                  </p>
                ) : null}
              </div>
            </div>
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">損益</p>
              <p className={`text-lg font-semibold ${getPLColorClass(holding.total_pl)}`}>
                {holding.total_pl ? formatCurrency(holding.total_pl) : "-"}
              </p>
            </div>
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">損益率</p>
              <p className={`text-lg font-semibold ${getPLColorClass(holding.total_pl_percentage)}`}>
                {holding.total_pl_percentage ? formatPercent(holding.total_pl_percentage) : "-"}
              </p>
            </div>
          </div>
        ) : (
          <p className="text-muted-foreground">保有情報が見つかりません</p>
        )}
      </CardContent>
    </Card>
  )
}
