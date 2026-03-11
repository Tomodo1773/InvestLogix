import { RefreshCw } from "lucide-react"
import useSWR from "swr"
import { AuthenticatedLayout } from "@/components/layout/authenticated-layout"
import { PortfolioHistoryTable } from "@/components/portfolio-history/portfolio-history-table"
import { Button } from "@/components/ui/button"
import { getPortfolioHistory } from "@/lib/api/client"
import { useAuthStore } from "@/lib/stores/auth-store"

export default function PortfolioHistory() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)

  const {
    data: history,
    isLoading,
    mutate,
  } = useSWR(isAuthenticated ? "/api/v1/portfolio/history" : null, getPortfolioHistory)

  const handleRefresh = () => {
    mutate()
  }

  return (
    <AuthenticatedLayout>
      <div className="mx-auto max-w-7xl space-y-6 p-4 md:p-6">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold">資産推移</h2>
          <Button variant="outline" size="sm" onClick={handleRefresh} disabled={isLoading}>
            <RefreshCw className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>
        <PortfolioHistoryTable history={history} isLoading={isLoading} />
      </div>
    </AuthenticatedLayout>
  )
}
