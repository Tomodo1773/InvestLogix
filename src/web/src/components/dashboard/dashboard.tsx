import { RefreshCw } from "lucide-react"
import { useMemo, useState } from "react"
import useSWR from "swr"
import { Button } from "@/components/ui/button"
import {
  getDividendsMonthly,
  getHoldings,
  getPortfolioHistory,
  getPortfolioSummary,
  getTransactionsMonthlySummary,
  getWeeklyPerformance,
} from "@/lib/api/client"
import { buildWeeklyChangeMap } from "@/lib/weekly-performance"
import { AssetChart } from "./asset-chart"
import { DividendAllocationChart } from "./dividend-allocation-chart"
import { DividendChart } from "./dividend-chart"
import { NisaLimitGauge } from "./nisa-limit-gauge"
import { SectorTreemap } from "./sector-treemap"
import { StatCards } from "./stat-cards"
import { TradeChart } from "./trade-chart"
import { WeeklyPerformanceCard } from "./weekly-performance-card"

export function Dashboard() {
  const {
    data: summary,
    isLoading: summaryLoading,
    mutate: mutateSummary,
  } = useSWR("portfolio-summary", getPortfolioSummary)

  const {
    data: history,
    isLoading: historyLoading,
    mutate: mutateHistory,
  } = useSWR("portfolio-history", getPortfolioHistory)

  const {
    data: trades,
    isLoading: tradesLoading,
    mutate: mutateTrades,
  } = useSWR("transactions-monthly", getTransactionsMonthlySummary)

  const {
    data: dividends,
    isLoading: dividendsLoading,
    mutate: mutateDividends,
  } = useSWR("dividends-monthly", getDividendsMonthly)

  const [refreshCount, setRefreshCount] = useState(0)

  const {
    data: weeklyPerformance,
    isLoading: weeklyPerformanceLoading,
    mutate: mutateWeeklyPerformance,
  } = useSWR("weekly-performance", getWeeklyPerformance)

  const {
    data: holdings,
    isLoading: holdingsLoading,
    mutate: mutateHoldings,
  } = useSWR("/api/v1/holdings/", getHoldings)

  const weeklyChangeMap = useMemo(() => buildWeeklyChangeMap(weeklyPerformance), [weeklyPerformance])

  const isRefreshing =
    summaryLoading ||
    historyLoading ||
    tradesLoading ||
    dividendsLoading ||
    weeklyPerformanceLoading ||
    holdingsLoading

  const handleRefresh = () => {
    mutateSummary()
    mutateHistory()
    mutateTrades()
    mutateDividends()
    mutateWeeklyPerformance()
    mutateHoldings()
    setRefreshCount((c) => c + 1)
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-4 md:p-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">ダッシュボード</h2>
        <Button variant="outline" size="sm" onClick={handleRefresh} disabled={isRefreshing}>
          <RefreshCw className={`h-4 w-4 ${isRefreshing ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>
      <StatCards summary={summary} isLoading={summaryLoading} />
      <NisaLimitGauge data={trades} isLoading={tradesLoading} />
      <AssetChart history={history} isLoading={historyLoading} />
      <div className="hidden md:block">
        <SectorTreemap data={holdings} isLoading={holdingsLoading} weeklyChangeMap={weeklyChangeMap} />
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <WeeklyPerformanceCard
          performers={weeklyPerformance?.top_performers}
          direction="top"
          isLoading={weeklyPerformanceLoading}
        />
        <WeeklyPerformanceCard
          performers={weeklyPerformance?.bottom_performers}
          direction="bottom"
          isLoading={weeklyPerformanceLoading}
        />
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <TradeChart data={trades} isLoading={tradesLoading} />
        <DividendChart data={dividends} isLoading={dividendsLoading} />
      </div>
      <DividendAllocationChart monthlyDividends={dividends} refreshSignal={refreshCount} />
    </div>
  )
}
