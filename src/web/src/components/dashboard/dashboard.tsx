import { RefreshCw } from "lucide-react"
import useSWR from "swr"
import { Button } from "@/components/ui/button"
import {
  getDividendsMonthly,
  getPortfolioHistory,
  getPortfolioSummary,
  getTransactionsMonthlySummary,
} from "@/lib/api/client"
import { AssetChart } from "./asset-chart"
import { DividendChart } from "./dividend-chart"
import { NisaLimitGauge } from "./nisa-limit-gauge"
import { StatCards } from "./stat-cards"
import { TradeChart } from "./trade-chart"

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

  const isRefreshing = summaryLoading || historyLoading || tradesLoading || dividendsLoading

  const handleRefresh = () => {
    mutateSummary()
    mutateHistory()
    mutateTrades()
    mutateDividends()
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
      <div className="grid gap-6 lg:grid-cols-2">
        <TradeChart data={trades} isLoading={tradesLoading} />
        <DividendChart data={dividends} isLoading={dividendsLoading} />
      </div>
    </div>
  )
}
