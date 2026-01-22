import { useMemo } from "react"
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { MonthlySummaryItem } from "@/lib/api/types"
import { formatCurrency, formatYearMonth } from "@/lib/format"

// 口座種別の英語→日本語マッピング
const ACCOUNT_NAME_MAP: Record<string, string> = {
  NISAAccumulation: "NISA(つみたて投資枠)",
  NISAGrowth: "NISA(成長投資枠)",
  juniorNISA: "ジュニアNISA",
  oldNISA: "旧NISA",
  specific: "特定",
}

const ACCOUNT_COLORS: Record<string, string> = {
  "NISA(つみたて投資枠)": "#2D9B81",
  "NISA(成長投資枠)": "#4CAF50",
  ジュニアNISA: "#2196F3",
  旧NISA: "#9C27B0",
  特定: "#FF9800",
}

interface TradeChartProps {
  data: MonthlySummaryItem[] | undefined
  isLoading: boolean
}

export function TradeChart({ data, isLoading }: TradeChartProps) {
  const { chartData, accountTypes } = useMemo(() => {
    if (!data || data.length === 0) {
      return { chartData: [], accountTypes: [] }
    }

    const types = new Set<string>()
    const processed = data.map((item) => {
      const entry: Record<string, string | number> = {
        month: formatYearMonth(item.year, item.month),
      }
      for (const [account, amount] of Object.entries(item.total_purchase)) {
        const displayName = ACCOUNT_NAME_MAP[account] || account
        types.add(displayName)
        entry[displayName] = amount
      }
      return entry
    })

    return { chartData: processed, accountTypes: Array.from(types) }
  }, [data])

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Trade Monthly</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-64 animate-pulse rounded bg-muted" />
        </CardContent>
      </Card>
    )
  }

  if (!chartData.length) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Trade Monthly</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex h-64 items-center justify-center text-muted-foreground">No data available</div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Trade Monthly</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E0E0E0" />
              <XAxis dataKey="month" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} tickFormatter={(v) => `${(v / 10000).toFixed(0)}万`} />
              <Tooltip
                formatter={(value: number | undefined) => {
                  if (value === undefined) return "-"
                  return formatCurrency(value)
                }}
              />
              <Legend />
              {accountTypes.map((account) => (
                <Bar
                  key={account}
                  dataKey={account}
                  stackId="a"
                  fill={ACCOUNT_COLORS[account] || "#888888"}
                  name={account}
                />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}
