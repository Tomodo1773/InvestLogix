import { useCallback, useMemo, useState } from "react"
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts"
import useSWR from "swr"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { getDividendAllocation } from "@/lib/api/client"
import { SWR_KEYS } from "@/lib/api/keys"
import type { DividendBySymbolItem, MonthlyDividendItem } from "@/lib/api/types"
import { CHART_COLORS, CHART_OTHER_COLOR } from "@/lib/chart-colors"
import { formatCurrency } from "@/lib/format"

interface DividendAllocationChartProps {
  monthlyDividends: MonthlyDividendItem[] | undefined
  refreshSignal: number
}

const OTHER_THRESHOLD_RATIO = 0.01

interface ChartDataItem {
  name: string
  symbol: string
  value: number
}

export function transformDividendsToChartData(
  dividends: DividendBySymbolItem[] | undefined
): ChartDataItem[] {
  if (!dividends || dividends.length === 0) return []

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

export function buildPeriodOptions(
  monthlyDividends: MonthlyDividendItem[] | undefined
): { value: string; label: string }[] {
  if (!monthlyDividends) return []
  return monthlyDividends
    .filter((m) => m.total_dividend > 0)
    .sort((a, b) => (b.year !== a.year ? b.year - a.year : b.month - a.month))
    .map((m) => ({
      value: `${m.year}-${String(m.month).padStart(2, "0")}`,
      label: `${m.year}年${m.month}月`,
    }))
}

export function DividendAllocationChart({ monthlyDividends, refreshSignal }: DividendAllocationChartProps) {
  const [selectedPeriod, setSelectedPeriod] = useState<string>("all")

  const swrParams = useMemo(() => {
    if (selectedPeriod === "all") return undefined
    const [y, m] = selectedPeriod.split("-")
    return { year: Number(y), month: Number(m) }
  }, [selectedPeriod])

  const fetcher = useCallback(() => getDividendAllocation(swrParams), [swrParams])

  const { data, isLoading } = useSWR(SWR_KEYS.dividendAllocation(selectedPeriod, refreshSignal), fetcher)

  const chartData = useMemo(() => transformDividendsToChartData(data), [data])
  const total = useMemo(() => chartData.reduce((sum, item) => sum + item.value, 0), [chartData])

  const periodOptions = useMemo(() => buildPeriodOptions(monthlyDividends), [monthlyDividends])

  const centerLabel = useMemo(() => {
    if (selectedPeriod === "all") return "累計配当"
    const [y, m] = selectedPeriod.split("-")
    return `${Number(y)}年${Number(m)}月`
  }, [selectedPeriod])

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>銘柄別配当割合</CardTitle>
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
        <Select value={selectedPeriod} onValueChange={setSelectedPeriod}>
          <SelectTrigger className="w-40">
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
