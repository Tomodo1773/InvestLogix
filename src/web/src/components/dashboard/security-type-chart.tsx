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

const VIEW_CONFIG: Record<
  ViewMode,
  {
    label: string
    title: string
    getKey: (h: Holding) => string
    colors: Record<string, string>
    labels: Record<string, string>
  }
> = {
  securityType: {
    label: "種別",
    title: "種別保有割合",
    getKey: (h) => h.security_type || "UNKNOWN",
    colors: { STOCK: "#2D9B81", ETF: "#D49A5A", REIT: "#9272A8", FUND: "#6DAA7C" },
    labels: { STOCK: "株式", ETF: "ETF", REIT: "REIT", FUND: "投資信託" },
  },
  currency: {
    label: "通貨",
    title: "通貨別保有割合",
    getKey: (h) => h.currency || "UNKNOWN",
    colors: { JPY: "#2D9B81", USD: "#D49A5A" },
    labels: { JPY: "円建て", USD: "ドル建て" },
  },
}

const VIEW_MODES: ViewMode[] = ["securityType", "currency"]

export function SecurityTypeChart({ data, isLoading }: SecurityTypeChartProps) {
  const [viewMode, setViewMode] = useState<ViewMode>("securityType")
  const config = VIEW_CONFIG[viewMode]

  const chartData = useMemo(() => {
    if (!data || data.length === 0) return []

    const grouped: Record<string, number> = {}
    for (const holding of data) {
      const key = config.getKey(holding)
      grouped[key] = (grouped[key] || 0) + (holding.market_value ?? 0)
    }

    return Object.entries(grouped)
      .map(([type, value]) => ({ name: config.labels[type] || type, value, type }))
      .filter((item) => item.value > 0)
      .sort((a, b) => b.value - a.value)
  }, [data, config])

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>{config.title}</CardTitle>
        <div className="flex gap-1">
          {VIEW_MODES.map((mode) => (
            <Button
              key={mode}
              variant={viewMode === mode ? "default" : "outline"}
              size="sm"
              onClick={() => setViewMode(mode)}
            >
              {VIEW_CONFIG[mode].label}
            </Button>
          ))}
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="h-64 animate-pulse rounded bg-muted" />
        ) : !chartData.length ? (
          <div className="flex h-64 items-center justify-center text-muted-foreground">No data available</div>
        ) : (
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={chartData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent, value }) =>
                    `${name} ${formatCurrency(Math.round(value))} (${((percent ?? 0) * 100).toFixed(0)}%)`
                  }
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {chartData.map((entry) => (
                    <Cell key={`cell-${entry.type}`} fill={config.colors[entry.type] || "#9E9E9E"} />
                  ))}
                </Pie>
                <Tooltip formatter={(value) => formatCurrency(typeof value === "number" ? value : 0)} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
