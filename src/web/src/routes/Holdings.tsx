import { RefreshCw } from "lucide-react"
import useSWR from "swr"
import { HoldingAllocationChart } from "@/components/dashboard/holding-allocation-chart"
import { HoldingsTable } from "@/components/dashboard/holdings-table"
import { SecurityTypeChart } from "@/components/dashboard/security-type-chart"
import { AuthenticatedLayout } from "@/components/layout/authenticated-layout"
import { Button } from "@/components/ui/button"
import { getHoldings } from "@/lib/api/client"
import { useAuthStore } from "@/lib/stores/auth-store"

export default function Holdings() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)

  const {
    data: holdings,
    isLoading,
    mutate,
  } = useSWR(isAuthenticated ? "/api/v1/holdings/" : null, getHoldings)

  const handleRefresh = () => {
    mutate()
  }

  return (
    <AuthenticatedLayout>
      <div className="mx-auto max-w-7xl space-y-6 p-4 md:p-6">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold">保有状況</h2>
          <Button variant="outline" size="sm" onClick={handleRefresh} disabled={isLoading}>
            <RefreshCw className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>
        <SecurityTypeChart data={holdings} isLoading={isLoading} />
        <HoldingAllocationChart data={holdings} isLoading={isLoading} />
        <HoldingsTable holdings={holdings} isLoading={isLoading} />
      </div>
    </AuthenticatedLayout>
  )
}
