import { useMemo, useState } from "react"
import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { Holding } from "@/lib/api/types"
import { formatCurrency } from "@/lib/format"

type ViewMode = "securityType" | "currency"

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

const CURRENCY_COLORS: Record<string, string> = {
  JPY: "#2196F3",
  USD: "#FF9800",
}

const CURRENCY_LABELS: Record<string, string> = {
  JPY: "円建て",
  USD: "ドル建て",
}

const VIEW_OPTIONS: { value: ViewMode; label: string }[] = [
  { value: "securityType", label: "種別" },
  { value: "currency", label: "通貨" },
]

export function SecurityTypeChart({ data, isLoading }: SecurityTypeChartProps) {
  const [viewMode, setViewMode] = useState<ViewMode>("securityType")

  const chartData = useMemo(() => {
    if (!data || data.length === 0) return []

    if (viewMode === "currency") {
      const grouped = data.reduce(
        (acc, holding) => {
          const currency = holding.currency || "UNKNOWN"
          const marketValue = holding.market_value ?? 0
          acc[currency] = (acc[currency] || 0) + marketValue
          return acc
        },
        {} as Record<string, number>
      )

      return Object.entries(grouped)
        .map(([type, value]) => ({
          name: CURRENCY_LABELS[type] || type,
          value,
          type,
        }))
        .filter((item) => item.value > 0)
        .sort((a, b) => b.value - a.value)
    }

    const grouped = data.reduce(
      (acc, holding) => {
        const securityType = holding.security_type || "UNKNOWN"
        const marketValue = holding.market_value ?? 0
        acc[securityType] = (acc[securityType] || 0) + marketValue
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
  }, [data, viewMode])

  const title = viewMode === "currency" ? "通貨別保有割合" : "種別保有割合"
  const colorMap = viewMode === "currency" ? CURRENCY_COLORS : SECURITY_TYPE_COLORS

  const toggleButtons = (
    <div className="flex gap-1">
      {VIEW_OPTIONS.map((option) => (
        <Button
          key={option.value}
          variant={viewMode === option.value ? "default" : "outline"}
          size="sm"
          onClick={() => setViewMode(option.value)}
        >
          {option.label}
        </Button>
      ))}
    </div>
  )

  if (isLoading) {
    return (
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>{title}</CardTitle>
          {toggleButtons}
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
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>{title}</CardTitle>
          {toggleButtons}
        </CardHeader>
        <CardContent>
          <div className="flex h-64 items-center justify-center text-muted-foreground">No data available</div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>{title}</CardTitle>
        {toggleButtons}
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
                  <Cell key={`cell-${entry.type}`} fill={colorMap[entry.type] || "#9E9E9E"} />
                ))}
              </Pie>
              <Tooltip
                formatter={(value) => formatCurrency(typeof value === "number" ? value : 0)}
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
