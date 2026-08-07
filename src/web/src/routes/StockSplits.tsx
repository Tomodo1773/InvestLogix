import { Plus, RefreshCw } from "lucide-react"
import { useState } from "react"
import useSWR, { mutate as revalidate } from "swr"
import { AuthenticatedLayout } from "@/components/layout/authenticated-layout"
import { StockSplitForm } from "@/components/stock-splits/stock-split-form"
import { StockSplitsTable } from "@/components/stock-splits/stock-splits-table"
import { Button } from "@/components/ui/button"
import { getStockSplits } from "@/lib/api/client"
import { SWR_KEYS } from "@/lib/api/keys"

export default function StockSplits() {
  const [isFormOpen, setIsFormOpen] = useState(false)

  const { data: stockSplits, isLoading, mutate } = useSWR(SWR_KEYS.stockSplits, () => getStockSplits())

  const handleRefresh = () => {
    mutate()
  }

  const handleCreated = () => {
    setIsFormOpen(false)
    mutate()
    // 分割登録は過去取引の調整値を再計算するため、取引と保有状況のキャッシュも古くなる。
    // 銘柄別のキー（?symbol=... 付き）も落とすので前方一致で判定する
    revalidate(
      (key) =>
        typeof key === "string" &&
        (key.startsWith(SWR_KEYS.transactions) || key.startsWith(SWR_KEYS.holdings))
    )
  }

  return (
    <AuthenticatedLayout>
      <div className="mx-auto max-w-7xl space-y-6 p-4 md:p-6">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold">株式分割</h2>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={handleRefresh} disabled={isLoading}>
              <RefreshCw className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
              Refresh
            </Button>
            <Button size="sm" onClick={() => setIsFormOpen(true)} disabled={isFormOpen}>
              <Plus className="h-4 w-4" />
              登録
            </Button>
          </div>
        </div>
        {isFormOpen && <StockSplitForm onCreated={handleCreated} onCancel={() => setIsFormOpen(false)} />}
        <StockSplitsTable stockSplits={stockSplits} isLoading={isLoading} />
      </div>
    </AuthenticatedLayout>
  )
}
