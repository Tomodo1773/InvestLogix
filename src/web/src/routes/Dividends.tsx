import { RefreshCw } from "lucide-react"
import { useState } from "react"
import useSWR from "swr"
import { DividendAllocationChart } from "@/components/dashboard/dividend-allocation-chart"
import { DividendChart } from "@/components/dashboard/dividend-chart"
import { DividendsTable } from "@/components/dividends/dividends-table"
import { Button } from "@/components/ui/button"
import { getDividends, getDividendsMonthly } from "@/lib/api/client"
import { SWR_KEYS } from "@/lib/api/keys"

export default function Dividends() {
  const [refreshCount, setRefreshCount] = useState(0)

  const { data: dividends, isLoading, mutate } = useSWR(SWR_KEYS.dividends, getDividends)

  const {
    data: dividendsMonthly,
    isLoading: monthlyLoading,
    mutate: mutateMonthly,
  } = useSWR(SWR_KEYS.dividendsMonthly, getDividendsMonthly)

  const isRefreshing = isLoading || monthlyLoading

  const handleRefresh = () => {
    mutate()
    mutateMonthly()
    setRefreshCount((c) => c + 1)
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-4 md:p-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">配当金履歴</h2>
        <Button variant="outline" size="sm" onClick={handleRefresh} disabled={isRefreshing}>
          <RefreshCw className={`h-4 w-4 ${isRefreshing ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <DividendChart data={dividendsMonthly} isLoading={monthlyLoading} />
        <DividendAllocationChart monthlyDividends={dividendsMonthly} refreshSignal={refreshCount} />
      </div>
      <DividendsTable dividends={dividends} isLoading={isLoading} />
    </div>
  )
}
