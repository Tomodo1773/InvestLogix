import { RefreshCw } from "lucide-react"
import useSWR from "swr"
import { AuthenticatedLayout } from "@/components/layout/authenticated-layout"
import { StocksTable } from "@/components/stocks/stocks-table"
import { Button } from "@/components/ui/button"
import { getStocks } from "@/lib/api/client"
import { SWR_KEYS } from "@/lib/api/keys"

export default function Stocks() {
  const { data: stocks, isLoading, mutate } = useSWR(SWR_KEYS.stocks, () => getStocks())

  const handleRefresh = () => {
    mutate()
  }

  return (
    <AuthenticatedLayout>
      <div className="mx-auto max-w-7xl space-y-6 p-4 md:p-6">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold">銘柄マスター</h2>
          <Button variant="outline" size="sm" onClick={handleRefresh} disabled={isLoading}>
            <RefreshCw className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>
        <StocksTable stocks={stocks} isLoading={isLoading} />
      </div>
    </AuthenticatedLayout>
  )
}
