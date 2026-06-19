import { useMemo, useState } from "react"
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { Holding } from "@/lib/api/types"
import { CHART_COLORS, CHART_OTHER_COLOR } from "@/lib/chart-colors"
import { formatCurrency } from "@/lib/format"
import { SECURITY_TYPE_FILTERS, type SecurityTypeFilter } from "@/lib/security-type"

interface HoldingAllocationChartProps {
  data: Holding[] | undefined
  isLoading: boolean
}

interface ChartDataItem {
  name: string
  symbol: string
  value: number
  [key: string]: string | number
}

/**
 * 保有銘柄データを円グラフ用に変換する
 * 上位20銘柄を個別に表示し、21位以降は「その他」として集約する
 * @param holdings 保有銘柄データ
 * @param filter セキュリティタイプフィルタ（デフォルト: "ALL"）
 */
export function transformHoldingsToChartData(
  holdings: Holding[] | undefined,
  filter: SecurityTypeFilter = "ALL"
): ChartDataItem[] {
  if (!holdings || holdings.length === 0) return []

  // フィルタを適用
  let filteredHoldings = holdings
  if (filter !== "ALL") {
    filteredHoldings = holdings.filter((holding) => holding.security_type === filter)
  }

  // 評価額でソート
  const sortedHoldings = [...filteredHoldings]
    .map((holding) => ({
      symbol: holding.symbol,
      name: holding.stock_name || holding.symbol,
      value: holding.market_value ?? 0,
    }))
    .filter((item) => item.value > 0)
    .sort((a, b) => b.value - a.value)

  // 上位20件
  const top20 = sortedHoldings.slice(0, 20)

  // 21位以降を「その他」として集約
  const others = sortedHoldings.slice(20)
  const othersTotal = others.reduce((sum, item) => sum + item.value, 0)

  const result = top20.map((item) => ({
    name: item.name,
    symbol: item.symbol,
    value: item.value,
  }))

  // 「その他」を追加（存在する場合のみ）
  if (othersTotal > 0) {
    result.push({
      name: "その他",
      symbol: "OTHER",
      value: othersTotal,
    })
  }

  return result
}

export function HoldingAllocationChart({ data, isLoading }: HoldingAllocationChartProps) {
  const [filter, setFilter] = useState<SecurityTypeFilter>("ALL")
  const chartData = useMemo(() => transformHoldingsToChartData(data, filter), [data, filter])

  // 全体の合計を計算（パーセンテージ表示用）
  const total = useMemo(() => {
    return chartData.reduce((sum, item) => sum + item.value, 0)
  }, [chartData])

  // フィルタに応じたタイトルを生成
  const chartTitle = useMemo(() => {
    const filterLabel = SECURITY_TYPE_FILTERS.find((option) => option.value === filter)?.label || "すべて"
    return filter === "ALL" ? "銘柄別保有割合" : `${filterLabel}の銘柄別保有割合`
  }, [filter])

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{chartTitle}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-80 animate-pulse rounded bg-muted" />
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{chartTitle}</CardTitle>
        <div className="mt-4 flex flex-wrap gap-2">
          {SECURITY_TYPE_FILTERS.map((option) => (
            <Button
              key={option.value}
              variant={filter === option.value ? "default" : "outline"}
              size="sm"
              onClick={() => setFilter(option.value)}
            >
              {option.label}
            </Button>
          ))}
        </div>
      </CardHeader>
      <CardContent>
        {!chartData.length ? (
          <div className="flex h-80 items-center justify-center text-muted-foreground">
            データがありません
          </div>
        ) : (
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={chartData}
                  cx="50%"
                  cy="50%"
                  startAngle={90}
                  endAngle={-270}
                  labelLine={false}
                  label={({ name, value }) => {
                    const percent = ((value / total) * 100).toFixed(1)
                    if (parseFloat(percent) < 2) return ""
                    const n = name ?? ""
                    const label = n.length > 20 ? `${n.slice(0, 20)}…` : n
                    return `${label} ${percent}%`
                  }}
                  outerRadius={120}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {chartData.map((entry, index) => (
                    <Cell
                      key={`cell-${entry.symbol}`}
                      fill={
                        entry.symbol === "OTHER"
                          ? CHART_OTHER_COLOR
                          : CHART_COLORS[index % CHART_COLORS.length]
                      }
                    />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(value, _name, props) => {
                    const numValue = typeof value === "number" ? value : 0
                    const percent = (numValue / total) * 100
                    const payload = props as { payload: { name: string } }
                    return [`${formatCurrency(numValue)} (${percent.toFixed(2)}%)`, payload.payload.name]
                  }}
                  labelFormatter={(label, payload) => {
                    if (payload && payload.length > 0) {
                      return payload[0].payload.name
                    }
                    return label
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
