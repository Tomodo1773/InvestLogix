import { TrendingDown, TrendingUp } from "lucide-react"
import { Link } from "react-router"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { StockWeeklyPerformance } from "@/lib/api/types"
import { formatPercent, getPLColorClass } from "@/lib/format"

interface WeeklyPerformanceCardProps {
  performers: StockWeeklyPerformance[] | undefined
  direction: "top" | "bottom"
  isLoading: boolean
}

const DIRECTION_META = {
  top: {
    title: "今週の値上がりトップ5",
    Icon: TrendingUp,
    iconColor: "text-success",
  },
  bottom: {
    title: "今週の値下がりトップ5",
    Icon: TrendingDown,
    iconColor: "text-destructive",
  },
}

function PerformerList({ performers }: { performers: StockWeeklyPerformance[] }) {
  return (
    <ul className="space-y-2">
      {performers.map((p, index) => (
        <li key={p.symbol} className="flex items-center justify-between gap-3 border-b py-2 last:border-b-0">
          <div className="flex min-w-0 items-center gap-3">
            <span className="w-5 shrink-0 text-sm text-muted-foreground">{index + 1}</span>
            <Link to={`/holdings/${p.symbol}`} className="min-w-0 hover:opacity-80">
              <p className="truncate text-sm font-medium">{p.name}</p>
              <p className="text-xs text-muted-foreground">{p.symbol}</p>
            </Link>
          </div>
          <span className={`shrink-0 font-bold ${getPLColorClass(p.change_rate)}`}>
            {formatPercent(p.change_rate)}
          </span>
        </li>
      ))}
    </ul>
  )
}

export function WeeklyPerformanceCard({ performers, direction, isLoading }: WeeklyPerformanceCardProps) {
  const meta = DIRECTION_META[direction]

  const renderBody = () => {
    if (isLoading) {
      return <div className="h-40 animate-pulse rounded bg-muted" />
    }
    if (!performers || performers.length === 0) {
      return <p className="text-sm text-muted-foreground">表示できる銘柄がありません</p>
    }
    return <PerformerList performers={performers} />
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <meta.Icon className={`h-5 w-5 ${meta.iconColor}`} />
          {meta.title}
        </CardTitle>
      </CardHeader>
      <CardContent>{renderBody()}</CardContent>
    </Card>
  )
}
