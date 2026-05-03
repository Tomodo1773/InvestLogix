import { ArrowLeft } from "lucide-react"
import { Link, useParams } from "react-router"
import useSWR from "swr"
import { AuthProvider } from "@/components/AuthProvider"
import { HoldingDividendsSection } from "@/components/holding-detail/HoldingDividendsSection"
import { HoldingNoteSection } from "@/components/holding-detail/HoldingNoteSection"
import { HoldingStockSplitsSection } from "@/components/holding-detail/HoldingStockSplitsSection"
import { HoldingSummarySection } from "@/components/holding-detail/HoldingSummarySection"
import { HoldingTransactionsSection } from "@/components/holding-detail/HoldingTransactionsSection"
import { AppLayout } from "@/components/layout/app-layout"
import { PriceChart } from "@/components/stock/price-chart"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import {
  getDividendsBySymbol,
  getHoldingBySymbol,
  getStockSplits,
  getTransactionsBySymbol,
} from "@/lib/api/client"
import { formatCurrency } from "@/lib/format"
import { useAuthStore } from "@/lib/stores/auth-store"

function HoldingDetailContent() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  const { symbol } = useParams<{ symbol: string }>()

  const {
    data: holdings,
    isLoading: isLoadingHolding,
    mutate: mutateHolding,
  } = useSWR(isAuthenticated && symbol ? `/holdings/${symbol}` : null, () =>
    symbol ? getHoldingBySymbol(symbol) : null
  )

  const { data: transactions, isLoading: isLoadingTransactions } = useSWR(
    isAuthenticated && symbol ? `/transactions/${symbol}` : null,
    () => (symbol ? getTransactionsBySymbol(symbol) : null)
  )

  const { data: dividends, isLoading: isLoadingDividends } = useSWR(
    isAuthenticated && symbol ? `/dividends/${symbol}` : null,
    () => (symbol ? getDividendsBySymbol(symbol) : null)
  )

  const { data: stockSplits, isLoading: isLoadingStockSplits } = useSWR(
    isAuthenticated && symbol ? `/stock-splits/${symbol}` : null,
    () => (symbol ? getStockSplits(symbol) : null)
  )

  const holding = holdings?.[0]

  if (!isAuthenticated) {
    return null
  }

  if (!symbol) {
    return (
      <AppLayout>
        <div className="flex min-h-screen items-center justify-center">
          <p className="text-muted-foreground">銘柄が指定されていません</p>
        </div>
      </AppLayout>
    )
  }

  return (
    <AppLayout>
      <div className="mx-auto max-w-7xl space-y-6 p-4 md:p-6">
        <div className="flex items-center gap-2">
          <Link to="/holdings">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="h-4 w-4 mr-1" />
              戻る
            </Button>
          </Link>
        </div>

        {/* 銘柄情報ヘッダー */}
        <Card>
          <CardContent className="pt-6">
            {isLoadingHolding ? (
              <div className="space-y-2">
                <div className="h-8 w-48 animate-pulse rounded bg-muted" />
                <div className="h-6 w-32 animate-pulse rounded bg-muted" />
              </div>
            ) : holding ? (
              <div className="space-y-2">
                <h1 className="text-2xl font-bold">
                  {holding.stock_name || symbol} ({symbol})
                </h1>
                <p className="text-xl text-muted-foreground">
                  現在価格: {holding.current_price ? formatCurrency(holding.current_price) : "取得中..."}
                </p>
              </div>
            ) : (
              <div className="space-y-2">
                <h1 className="text-2xl font-bold">{symbol}</h1>
                <p className="text-muted-foreground">保有情報が見つかりません</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* 保有状況サマリ */}
        <HoldingSummarySection holding={holding} isLoading={isLoadingHolding} />

        {/* メモ */}
        <HoldingNoteSection
          symbol={symbol}
          note={holding?.note ?? null}
          isLoading={isLoadingHolding}
          onSaved={() => mutateHolding()}
        />

        {/* 株価グラフ */}
        <PriceChart
          symbol={symbol}
          securityType={holding?.security_type}
          transactions={transactions ?? undefined}
        />

        {/* 取引履歴 */}
        <HoldingTransactionsSection
          transactions={transactions ?? undefined}
          isLoading={isLoadingTransactions}
        />

        {/* 配当金履歴 */}
        <HoldingDividendsSection dividends={dividends ?? undefined} isLoading={isLoadingDividends} />

        {/* 株式分割履歴 */}
        <HoldingStockSplitsSection stockSplits={stockSplits ?? undefined} isLoading={isLoadingStockSplits} />
      </div>
    </AppLayout>
  )
}

export default function HoldingDetail() {
  return (
    <AuthProvider>
      <HoldingDetailContent />
    </AuthProvider>
  )
}
