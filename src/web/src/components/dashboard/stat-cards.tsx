import { BarChart3, Coins, TrendingUp, Wallet } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import type { PortfolioSummary } from "@/lib/api/types"
import { formatCurrency, formatPercent } from "@/lib/format"

interface StatCardsProps {
  summary: PortfolioSummary | undefined
  isLoading: boolean
}

export function StatCards({ summary, isLoading }: StatCardsProps) {
  const stats = [
    {
      label: "Total P/L",
      value: summary ? formatCurrency(summary.total_pl) : "-",
      icon: Wallet,
      color: summary && Number(summary.total_pl) >= 0 ? "text-[#4CAF50]" : "text-destructive",
      bgColor: summary && Number(summary.total_pl) >= 0 ? "bg-[#4CAF50]/10" : "bg-destructive/10",
    },
    {
      label: "P/L Rate",
      value: summary ? formatPercent(summary.total_unrealized_pl_percentage) : "-",
      icon: TrendingUp,
      color:
        summary && Number(summary.total_unrealized_pl_percentage) >= 0
          ? "text-[#4CAF50]"
          : "text-destructive",
      bgColor:
        summary && Number(summary.total_unrealized_pl_percentage) >= 0
          ? "bg-[#4CAF50]/10"
          : "bg-destructive/10",
    },
    {
      label: "Market Value",
      value: summary ? formatCurrency(summary.total_market_value) : "-",
      icon: BarChart3,
      color: "text-[#2196F3]",
      bgColor: "bg-[#2196F3]/10",
    },
    {
      label: "Total Dividend",
      value: summary ? formatCurrency(summary.total_dividend) : "-",
      icon: Coins,
      color: "text-secondary",
      bgColor: "bg-secondary/10",
    },
  ]

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {stats.map((stat) => (
        <Card key={stat.label} className="py-4">
          <CardContent className="flex items-center gap-4">
            <div className={`flex h-12 w-12 items-center justify-center rounded-lg ${stat.bgColor}`}>
              <stat.icon className={`h-6 w-6 ${stat.color}`} />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">{stat.label}</p>
              {isLoading ? (
                <div className="h-7 w-24 animate-pulse rounded bg-muted" />
              ) : (
                <p className={`text-xl font-bold ${stat.color}`}>{stat.value}</p>
              )}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
