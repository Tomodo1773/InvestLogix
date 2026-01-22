import { RefreshCw } from "lucide-react"
import useSWR from "swr"
import { AuthProvider } from "@/components/AuthProvider"
import { DividendsTable } from "@/components/dividends/dividends-table"
import { AppLayout } from "@/components/layout/app-layout"
import { Button } from "@/components/ui/button"
import { getDividends } from "@/lib/api/client"
import { useAuthStore } from "@/lib/stores/auth-store"

function DividendsContent() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)

  const {
    data: dividends,
    isLoading,
    mutate,
  } = useSWR(isAuthenticated ? "/api/v1/dividends/" : null, getDividends)

  const handleRefresh = () => {
    mutate()
  }

  if (!isAuthenticated) {
    return null
  }

  return (
    <AppLayout>
      <div className="mx-auto max-w-7xl space-y-6 p-6">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold">配当金履歴</h2>
          <Button variant="outline" size="sm" onClick={handleRefresh} disabled={isLoading}>
            <RefreshCw className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>
        <DividendsTable dividends={dividends} isLoading={isLoading} />
      </div>
    </AppLayout>
  )
}

export default function Dividends() {
  return (
    <AuthProvider>
      <DividendsContent />
    </AuthProvider>
  )
}
