import { useMemo, useState } from "react"
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { Holding } from "@/lib/api/types"
import { formatCurrency } from "@/lib/format"

interface HoldingAllocationChartProps {
  data: Holding[] | undefined
  isLoading: boolean
}

// 上位20銘柄用の色パレット（区別しやすい色を選定）
const COLORS = [
  "#2196F3", // Blue
  "#FF9800", // Orange
  "#4CAF50", // Green
  "#9C27B0", // Purple
  "#F44336", // Red
  "#00BCD4", // Cyan
  "#FFEB3B", // Yellow
  "#795548", // Brown
  "#E91E63", // Pink
  "#3F51B5", // Indigo
  "#009688", // Teal
  "#FF5722", // Deep Orange
  "#8BC34A", // Light Green
  "#673AB7", // Deep Purple
  "#FFC107", // Amber
  "#607D8B", // Blue Grey
  "#CDDC39", // Lime
  "#9E9E9E", // Grey
  "#00E676", // Green A400
  "#FF6F00", // Orange 900
]

// 「その他」用の色
const OTHER_COLOR = "#BDBDBD"

// フィルタータイプ
type SecurityTypeFilter = "ALL" | "STOCK" | "ETF" | "FUND" | "REIT"

// フィルタボタンの設定
const FILTER_OPTIONS: { value: SecurityTypeFilter; label: string }[] = [
  { value: "ALL", label: "すべて" },
  { value: "STOCK", label: "株式" },
  { value: "ETF", label: "ETF" },
  { value: "FUND", label: "投信" },
  { value: "REIT", label: "REIT" },
]

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
    const filterLabel = FILTER_OPTIONS.find((option) => option.value === filter)?.label || "すべて"
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
          {FILTER_OPTIONS.map((option) => (
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
                  labelLine={false}
                  label={({ name, value }) => {
                    const percent = ((value / total) * 100).toFixed(1)
                    // 小さいセクター（2%未満）はラベルを省略
                    if (parseFloat(percent) < 2) return ""
                    return `${name} ${percent}%`
                  }}
                  outerRadius={120}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {chartData.map((entry, index) => (
                    <Cell
                      key={`cell-${entry.symbol}`}
                      fill={entry.symbol === "OTHER" ? OTHER_COLOR : COLORS[index % COLORS.length]}
                    />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(value: number | undefined, _name: string | undefined, props: unknown) => {
                    const percent = ((value ?? 0) / total) * 100
                    const payload = props as { payload: { name: string } }
                    return [`${formatCurrency(value ?? 0)} (${percent.toFixed(2)}%)`, payload.payload.name]
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
