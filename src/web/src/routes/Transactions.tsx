import { RefreshCw } from "lucide-react"
import useSWR from "swr"
import { AuthenticatedLayout } from "@/components/layout/authenticated-layout"
import { TransactionsTable } from "@/components/transactions/transactions-table"
import { Button } from "@/components/ui/button"
import { getTransactions } from "@/lib/api/client"
import { useAuthStore } from "@/lib/stores/auth-store"

export default function Transactions() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)

  const {
    data: transactions,
    isLoading,
    mutate,
  } = useSWR(isAuthenticated ? "/api/v1/transactions/" : null, getTransactions)

  const handleRefresh = () => {
    mutate()
  }

  return (
    <AuthenticatedLayout>
      <div className="mx-auto max-w-7xl space-y-6 p-6">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold">取引履歴</h2>
          <Button variant="outline" size="sm" onClick={handleRefresh} disabled={isLoading}>
            <RefreshCw className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>
        <TransactionsTable transactions={transactions} isLoading={isLoading} />
      </div>
    </AuthenticatedLayout>
  )
}
