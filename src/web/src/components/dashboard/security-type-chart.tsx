import { useMemo } from "react"
import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { Holding } from "@/lib/api/types"
import { formatCurrency } from "@/lib/format"

interface SecurityTypeChartProps {
  data: Holding[] | undefined
  isLoading: boolean
}

const SECURITY_TYPE_COLORS: Record<string, string> = {
  STOCK: "#2196F3",
  ETF: "#FF9800",
  REIT: "#9C27B0",
  FUND: "#4CAF50",
}

const SECURITY_TYPE_LABELS: Record<string, string> = {
  STOCK: "株式",
  ETF: "ETF",
  REIT: "REIT",
  FUND: "投資信託",
}

export function SecurityTypeChart({ data, isLoading }: SecurityTypeChartProps) {
  const chartData = useMemo(() => {
    if (!data || data.length === 0) return []

    const grouped = data.reduce(
      (acc, holding) => {
        const securityType = holding.security_type || "UNKNOWN"
        const marketValue = holding.market_value ?? 0

        if (!acc[securityType]) {
          acc[securityType] = 0
        }
        acc[securityType] += marketValue

        return acc
      },
      {} as Record<string, number>
    )

    return Object.entries(grouped)
      .map(([type, value]) => ({
        name: SECURITY_TYPE_LABELS[type] || type,
        value,
        type,
      }))
      .filter((item) => item.value > 0)
      .sort((a, b) => b.value - a.value)
  }, [data])

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Holdings by Security Type</CardTitle>
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
          <CardTitle>Holdings by Security Type</CardTitle>
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
        <CardTitle>Holdings by Security Type</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`}
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
              >
                {chartData.map((entry) => (
                  <Cell key={`cell-${entry.type}`} fill={SECURITY_TYPE_COLORS[entry.type] || "#9E9E9E"} />
                ))}
              </Pie>
              <Tooltip
                formatter={(value: number | undefined) => formatCurrency(value ?? 0)}
                labelFormatter={(label) => `${label}`}
              />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}
