import { RefreshCw } from "lucide-react"
import useSWR from "swr"
import { DividendAllocationChart } from "@/components/dashboard/dividend-allocation-chart"
import { DividendChart } from "@/components/dashboard/dividend-chart"
import { DividendsTable } from "@/components/dividends/dividends-table"
import { AuthenticatedLayout } from "@/components/layout/authenticated-layout"
import { Button } from "@/components/ui/button"
import { getDividendAllocation, getDividends, getDividendsMonthly } from "@/lib/api/client"
import { useAuthStore } from "@/lib/stores/auth-store"

export default function Dividends() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)

  const {
    data: dividends,
    isLoading,
    mutate,
  } = useSWR(isAuthenticated ? "/api/v1/dividends/" : null, getDividends)

  const {
    data: dividendsMonthly,
    isLoading: monthlyLoading,
    mutate: mutateMonthly,
  } = useSWR(isAuthenticated ? "dividends-monthly" : null, getDividendsMonthly)

  const {
    data: dividendsBySymbol,
    isLoading: bySymbolLoading,
    mutate: mutateBySymbol,
  } = useSWR(isAuthenticated ? "dividends-by-symbol" : null, getDividendAllocation)

  const isRefreshing = isLoading || monthlyLoading || bySymbolLoading

  const handleRefresh = () => {
    mutate()
    mutateMonthly()
    mutateBySymbol()
  }

  return (
    <AuthenticatedLayout>
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
          <DividendAllocationChart data={dividendsBySymbol} isLoading={bySymbolLoading} />
        </div>
        <DividendsTable dividends={dividends} isLoading={isLoading} />
      </div>
    </AuthenticatedLayout>
  )
}
