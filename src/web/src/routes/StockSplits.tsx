import { RefreshCw } from "lucide-react"
import useSWR from "swr"
import { AuthenticatedLayout } from "@/components/layout/authenticated-layout"
import { StockSplitsTable } from "@/components/stock-splits/stock-splits-table"
import { Button } from "@/components/ui/button"
import { getStockSplits } from "@/lib/api/client"
import { useAuthStore } from "@/lib/stores/auth-store"

export default function StockSplits() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)

  const {
    data: stockSplits,
    isLoading,
    mutate,
  } = useSWR(isAuthenticated ? "/api/v1/stock-splits/" : null, () => getStockSplits())

  const handleRefresh = () => {
    mutate()
  }

  return (
    <AuthenticatedLayout>
      <div className="mx-auto max-w-7xl space-y-6 p-4 md:p-6">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold">株式分割履歴</h2>
          <Button variant="outline" size="sm" onClick={handleRefresh} disabled={isLoading}>
            <RefreshCw className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>
        <StockSplitsTable stockSplits={stockSplits} isLoading={isLoading} />
      </div>
    </AuthenticatedLayout>
  )
}
