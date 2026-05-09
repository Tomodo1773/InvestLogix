import { AlertCircle, Calculator, Download, RefreshCw } from "lucide-react"
import { useState } from "react"
import useSWR, { mutate as globalMutate } from "swr"
import { HoldingAllocationChart } from "@/components/dashboard/holding-allocation-chart"
import { HoldingsTable } from "@/components/dashboard/holdings-table"
import { SecurityTypeChart } from "@/components/dashboard/security-type-chart"
import { AuthenticatedLayout } from "@/components/layout/authenticated-layout"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { getHoldings, recalculateAllHoldings } from "@/lib/api/client"
import { downloadCsv, holdingsToCsv } from "@/lib/csv"
import { useAuthStore } from "@/lib/stores/auth-store"

export default function Holdings() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)

  const {
    data: holdings,
    isLoading,
    mutate,
  } = useSWR(isAuthenticated ? "/api/v1/holdings/" : null, getHoldings)

  const [isRecalculating, setIsRecalculating] = useState(false)
  const [recalcError, setRecalcError] = useState<string | null>(null)

  const handleRefresh = () => {
    mutate()
  }

  const handleRecalculate = async () => {
    setIsRecalculating(true)
    setRecalcError(null)
    try {
      const updated = await recalculateAllHoldings()
      await mutate(updated, { revalidate: false })
      globalMutate("portfolio-summary")
      globalMutate("portfolio-history")
      globalMutate("/api/v1/portfolio/history")
    } catch (e) {
      setRecalcError(e instanceof Error ? e.message : "再計算に失敗しました")
    } finally {
      setIsRecalculating(false)
    }
  }

  const activeHoldings = holdings?.filter((h) => h.quantity > 0) ?? []
  const exportDisabled = isLoading || activeHoldings.length === 0

  const handleExport = () => {
    if (activeHoldings.length === 0) return
    const now = new Date()
    const yyyymmdd = `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, "0")}${String(now.getDate()).padStart(2, "0")}`
    downloadCsv(`holdings_${yyyymmdd}.csv`, holdingsToCsv(activeHoldings))
  }

  return (
    <AuthenticatedLayout>
      <div className="mx-auto max-w-7xl space-y-6 p-4 md:p-6">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <h2 className="text-2xl font-bold">保有状況</h2>
          <div className="flex flex-wrap items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleRecalculate}
              disabled={isLoading || isRecalculating}
            >
              <Calculator className={`h-4 w-4 ${isRecalculating ? "animate-pulse" : ""}`} />
              {isRecalculating ? "再計算中..." : "全銘柄を再計算"}
            </Button>
            <Button variant="outline" size="sm" onClick={handleExport} disabled={exportDisabled}>
              <Download className="h-4 w-4" />
              CSVエクスポート
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleRefresh}
              disabled={isLoading || isRecalculating}
            >
              <RefreshCw className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
              再読み込み
            </Button>
          </div>
        </div>
        {recalcError && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>エラー</AlertTitle>
            <AlertDescription>{recalcError}</AlertDescription>
          </Alert>
        )}
        <SecurityTypeChart data={holdings} isLoading={isLoading} />
        <HoldingAllocationChart data={holdings} isLoading={isLoading} />
        <HoldingsTable holdings={holdings} isLoading={isLoading} />
      </div>
    </AuthenticatedLayout>
  )
}
