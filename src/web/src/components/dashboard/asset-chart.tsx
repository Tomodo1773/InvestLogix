import { useMemo, useState } from "react"
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { PortfolioHistoryItem } from "@/lib/api/types"
import { formatCurrency, formatPercent } from "@/lib/format"

type TimeFrame = "daily" | "monthly" | "yearly"

interface AssetChartProps {
  history: PortfolioHistoryItem[] | undefined
  isLoading: boolean
}

export function filterDataByTimeFrame(
  data: PortfolioHistoryItem[],
  timeFrame: TimeFrame
): PortfolioHistoryItem[] {
  if (!data || data.length === 0) return []

  if (timeFrame === "daily") {
    return data
  }

  const grouped = new Map<string, PortfolioHistoryItem>()

  for (const item of data) {
    const date = new Date(item.date)
    const key = timeFrame === "monthly" ? `${date.getFullYear()}-${date.getMonth()}` : `${date.getFullYear()}`
    grouped.set(key, item)
  }

  return Array.from(grouped.values())
}

export function AssetChart({ history, isLoading }: AssetChartProps) {
  const [timeFrame, setTimeFrame] = useState<TimeFrame>("monthly")

  const filteredData = useMemo(() => {
    return filterDataByTimeFrame(history || [], timeFrame)
  }, [history, timeFrame])

  const chartData = useMemo(() => {
    return filteredData.map((item) => ({
      ...item,
      rawDate: item.date,
      date: new Date(item.date).toLocaleDateString("ja-JP", {
        year: "2-digit",
        month: "short",
        day: timeFrame === "daily" ? "numeric" : undefined,
      }),
    }))
  }, [filteredData, timeFrame])

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Changes in Assets</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-80 animate-pulse rounded bg-muted" />
        </CardContent>
      </Card>
    )
  }

  if (!chartData.length) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Changes in Assets</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex h-80 items-center justify-center text-muted-foreground">No data available</div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Changes in Assets</CardTitle>
        <div className="flex gap-1">
          {(["daily", "monthly", "yearly"] as const).map((tf) => (
            <Button
              key={tf}
              variant={timeFrame === tf ? "default" : "outline"}
              size="sm"
              onClick={() => setTimeFrame(tf)}
            >
              {tf === "daily" ? "Daily" : tf === "monthly" ? "Monthly" : "Yearly"}
            </Button>
          ))}
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E0E0E0" />
              <XAxis dataKey="date" tick={{ fontSize: 12 }} />
              <YAxis
                yAxisId="left"
                width={60}
                tick={{ fontSize: 12 }}
                tickFormatter={(v) => `${(v / 1000000).toFixed(1)}M`}
              />
              <YAxis
                yAxisId="right"
                orientation="right"
                width={50}
                tick={{ fontSize: 12 }}
                tickFormatter={(v) => `${v}%`}
              />
              <Tooltip
                formatter={(value: number | undefined, name: string | undefined) => {
                  if (value === undefined) return ["-", name ?? ""]
                  if (name === "total_unrealized_pl_percentage") {
                    return [formatPercent(value), "Unrealized P/L %"]
                  }
                  return [formatCurrency(value), name === "total_cost" ? "Total Cost" : "Market Value"]
                }}
              />
              <Line
                yAxisId="left"
                type="monotone"
                dataKey="total_cost"
                stroke="#2196F3"
                strokeWidth={2}
                dot={false}
                name="total_cost"
              />
              <Line
                yAxisId="left"
                type="monotone"
                dataKey="total_market_value"
                stroke="#4CAF50"
                strokeWidth={2}
                dot={false}
                name="total_market_value"
              />
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="total_unrealized_pl_percentage"
                stroke="#F44336"
                strokeWidth={2}
                dot={false}
                name="total_unrealized_pl_percentage"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="h-40">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E0E0E0" />
              <XAxis dataKey="date" tick={{ fontSize: 12 }} />
              <YAxis
                width={60}
                tick={{ fontSize: 12 }}
                tickFormatter={(v) => `${(v / 1000000).toFixed(1)}M`}
              />
              <YAxis yAxisId="right" orientation="right" width={50} tick={false} axisLine={false} />
              <Tooltip
                formatter={(value: number | undefined) => {
                  if (value === undefined) return ["-", "Unrealized P/L"]
                  return [formatCurrency(value), "Unrealized P/L"]
                }}
              />
              <ReferenceLine y={0} stroke="#666" />
              <Bar dataKey="total_unrealized_pl" name="Unrealized P/L">
                {chartData.map((entry) => (
                  <Cell key={entry.rawDate} fill={entry.total_unrealized_pl >= 0 ? "#4CAF50" : "#F44336"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}
