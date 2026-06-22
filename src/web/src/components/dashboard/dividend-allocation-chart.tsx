import { useMemo, useState } from "react"
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts"
import useSWR from "swr"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { getDividendAllocation } from "@/lib/api/client"
import type { DividendBySymbolItem, MonthlyDividendItem } from "@/lib/api/types"
import { CHART_COLORS, CHART_OTHER_COLOR } from "@/lib/chart-colors"
import { formatCurrency } from "@/lib/format"

interface DividendAllocationChartProps {
  monthlyDividends: MonthlyDividendItem[] | undefined
  refreshSignal: number
}

// 累計配当に占める割合がこの値未満の銘柄を「その他」に集約する
const OTHER_THRESHOLD_RATIO = 0.01

interface ChartDataItem {
  name: string
  symbol: string
  value: number
}

/**
 * 銘柄別配当データをドーナツグラフ用に変換する
 * 累計配当に占める割合が OTHER_THRESHOLD_RATIO 未満の銘柄を「その他」に集約し、
 * しきい値以上の銘柄はすべて金額降順で個別表示する。
 * @param dividends 銘柄別配当データ
 */
export function transformDividendsToChartData(
  dividends: DividendBySymbolItem[] | undefined
): ChartDataItem[] {
  if (!dividends || dividends.length === 0) return []

  // 配当額が正の銘柄のみを金額降順でソート
  const sorted = dividends
    .map((item) => ({
      symbol: item.symbol,
      name: item.stock_name || item.symbol,
      value: item.total_dividend,
    }))
    .filter((item) => item.value > 0)
    .sort((a, b) => b.value - a.value)

  const total = sorted.reduce((sum, item) => sum + item.value, 0)
  if (total === 0) return []

  // しきい値以上は個別表示、しきい値未満は「その他」に集約
  const result: ChartDataItem[] = []
  let othersTotal = 0
  for (const item of sorted) {
    if (item.value / total >= OTHER_THRESHOLD_RATIO) {
      result.push(item)
    } else {
      othersTotal += item.value
    }
  }

  if (othersTotal > 0) {
    result.push({ name: "その他", symbol: "OTHER", value: othersTotal })
  }

  return result
}

export function DividendAllocationChart({ monthlyDividends, refreshSignal }: DividendAllocationChartProps) {
  const [selectedPeriod, setSelectedPeriod] = useState("all")

  const periodOptions = useMemo(() => {
    if (!monthlyDividends) return []
    return monthlyDividends
      .filter((d) => d.total_dividend > 0)
      .sort((a, b) => b.year - a.year || b.month - a.month)
      .map((d) => ({
        value: `${d.year}-${String(d.month).padStart(2, "0")}`,
        label: `${d.year}年${d.month}月`,
      }))
  }, [monthlyDividends])

  const params = useMemo(() => {
    if (selectedPeriod === "all") return undefined
    const [y, m] = selectedPeriod.split("-")
    return { year: Number(y), month: Number(m) }
  }, [selectedPeriod])

  const { data, isLoading } = useSWR(["dividends-by-symbol", selectedPeriod, refreshSignal], () =>
    getDividendAllocation(params)
  )

  const chartData = useMemo(() => transformDividendsToChartData(data), [data])
  const total = useMemo(() => chartData.reduce((sum, item) => sum + item.value, 0), [chartData])

  const centerLabel =
    selectedPeriod === "all"
      ? "累計配当"
      : (periodOptions.find((o) => o.value === selectedPeriod)?.label ?? "")

  const periodSelect = (
    <Select value={selectedPeriod} onValueChange={setSelectedPeriod}>
      <SelectTrigger className="w-[140px]">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="all">通算</SelectItem>
        {periodOptions.map((opt) => (
          <SelectItem key={opt.value} value={opt.value}>
            {opt.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )

  if (isLoading) {
    return (
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0">
          <CardTitle>銘柄別配当割合</CardTitle>
          {periodSelect}
        </CardHeader>
        <CardContent>
          <div className="h-80 animate-pulse rounded bg-muted" />
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0">
        <CardTitle>銘柄別配当割合</CardTitle>
        {periodSelect}
      </CardHeader>
      <CardContent>
        {!chartData.length ? (
          <div className="flex h-80 items-center justify-center text-muted-foreground">
            データがありません
          </div>
        ) : (
          <div className="relative h-80">
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
                    if (parseFloat(percent) < 3) return ""
                    const n = name ?? ""
                    const label = n.length > 20 ? `${n.slice(0, 20)}…` : n
                    return `${label} ${percent}%`
                  }}
                  innerRadius={70}
                  outerRadius={110}
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
            <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
              <span className="text-xs text-muted-foreground">{centerLabel}</span>
              <span className="text-xl font-bold">{formatCurrency(total)}</span>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
