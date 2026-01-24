import { ArrowLeft } from "lucide-react"
import { Link, useParams } from "react-router"
import useSWR from "swr"
import { AuthProvider } from "@/components/AuthProvider"
import { AppLayout } from "@/components/layout/app-layout"
import { PriceChart } from "@/components/stock/price-chart"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { getDividendsBySymbol, getHoldingBySymbol, getTransactionsBySymbol } from "@/lib/api/client"
import { formatCurrency, formatDate, formatPercent } from "@/lib/format"
import { useAuthStore } from "@/lib/stores/auth-store"

function HoldingDetailContent() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  const { symbol } = useParams<{ symbol: string }>()

  const { data: holdings, isLoading: isLoadingHolding } = useSWR(
    isAuthenticated && symbol ? `/holdings/${symbol}` : null,
    () => (symbol ? getHoldingBySymbol(symbol) : null)
  )

  const { data: transactions, isLoading: isLoadingTransactions } = useSWR(
    isAuthenticated && symbol ? `/transactions/${symbol}` : null,
    () => (symbol ? getTransactionsBySymbol(symbol) : null)
  )

  const { data: dividends, isLoading: isLoadingDividends } = useSWR(
    isAuthenticated && symbol ? `/dividends/${symbol}` : null,
    () => (symbol ? getDividendsBySymbol(symbol) : null)
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
      <div className="container mx-auto p-4 space-y-6">
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
        <Card>
          <CardHeader>
            <CardTitle>保有状況サマリ</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoadingHolding ? (
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-5">
                {[...Array(5)].map((_, i) => (
                  // biome-ignore lint/suspicious/noArrayIndexKey: Static skeleton loading elements
                  <div key={`skeleton-${i}`} className="space-y-2">
                    <div className="h-4 w-20 animate-pulse rounded bg-muted" />
                    <div className="h-6 w-24 animate-pulse rounded bg-muted" />
                  </div>
                ))}
              </div>
            ) : holding ? (
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-5">
                <div className="space-y-1">
                  <p className="text-sm text-muted-foreground">保有数</p>
                  <p className="text-lg font-semibold">{Number(holding.quantity).toLocaleString()}株</p>
                </div>
                <div className="space-y-1">
                  <p className="text-sm text-muted-foreground">平均取得単価</p>
                  <p className="text-lg font-semibold">{formatCurrency(holding.average_cost)}</p>
                </div>
                <div className="space-y-1">
                  <p className="text-sm text-muted-foreground">評価額</p>
                  <p className="text-lg font-semibold">
                    {holding.market_value ? formatCurrency(holding.market_value) : "-"}
                  </p>
                </div>
                <div className="space-y-1">
                  <p className="text-sm text-muted-foreground">損益</p>
                  <p
                    className={`text-lg font-semibold ${
                      holding.unrealized_pl && Number(holding.unrealized_pl) >= 0
                        ? "text-[#4CAF50]"
                        : "text-destructive"
                    }`}
                  >
                    {holding.unrealized_pl ? formatCurrency(holding.unrealized_pl) : "-"}
                  </p>
                </div>
                <div className="space-y-1">
                  <p className="text-sm text-muted-foreground">損益率</p>
                  <p
                    className={`text-lg font-semibold ${
                      holding.unrealized_pl_percentage && Number(holding.unrealized_pl_percentage) >= 0
                        ? "text-[#4CAF50]"
                        : "text-destructive"
                    }`}
                  >
                    {holding.unrealized_pl_percentage ? formatPercent(holding.unrealized_pl_percentage) : "-"}
                  </p>
                </div>
              </div>
            ) : (
              <p className="text-muted-foreground">保有情報が見つかりません</p>
            )}
          </CardContent>
        </Card>

        {/* 株価グラフ */}
        <PriceChart symbol={symbol} securityType={holding?.security_type} transactions={transactions ?? undefined} />

        {/* 取引履歴 */}
        <Card>
          <CardHeader>
            <CardTitle>取引履歴</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoadingTransactions ? (
              <div className="space-y-2">
                {[...Array(3)].map((_, i) => (
                  // biome-ignore lint/suspicious/noArrayIndexKey: Static skeleton loading elements
                  <div key={`skeleton-${i}`} className="h-12 animate-pulse rounded bg-muted" />
                ))}
              </div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>日付</TableHead>
                      <TableHead>種別</TableHead>
                      <TableHead className="text-right">数量</TableHead>
                      <TableHead className="text-right">単価</TableHead>
                      <TableHead className="text-right">手数料</TableHead>
                      <TableHead className="text-right">税金</TableHead>
                      <TableHead className="text-right">損益率</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {transactions && transactions.length > 0 ? (
                      transactions.map((transaction) => {
                        const displayPrice = transaction.adjusted_price || transaction.price
                        const displayQuantity = transaction.adjusted_quantity || transaction.quantity
                        const plValue =
                          transaction.unrealized_pl_percentage !== null &&
                          transaction.unrealized_pl_percentage !== undefined
                            ? Number(transaction.unrealized_pl_percentage)
                            : null
                        const plColor =
                          plValue !== null ? (plValue >= 0 ? "text-[#4CAF50]" : "text-destructive") : ""

                        return (
                          <TableRow key={transaction.transaction_id}>
                            <TableCell>{formatDate(transaction.transaction_date)}</TableCell>
                            <TableCell>
                              <span
                                className={
                                  transaction.transaction_type === "buy"
                                    ? "text-[#4CAF50]"
                                    : "text-destructive"
                                }
                              >
                                {transaction.transaction_type === "buy" ? "買付" : "売却"}
                              </span>
                            </TableCell>
                            <TableCell className="text-right">
                              {Number(displayQuantity).toLocaleString()}
                            </TableCell>
                            <TableCell className="text-right">{formatCurrency(displayPrice)}</TableCell>
                            <TableCell className="text-right">{formatCurrency(transaction.fee)}</TableCell>
                            <TableCell className="text-right">{formatCurrency(transaction.tax)}</TableCell>
                            <TableCell className={`text-right font-medium ${plColor}`}>
                              {transaction.transaction_type === "buy" &&
                              transaction.unrealized_pl_percentage !== null &&
                              transaction.unrealized_pl_percentage !== undefined
                                ? formatPercent(transaction.unrealized_pl_percentage)
                                : "-"}
                            </TableCell>
                          </TableRow>
                        )
                      })
                    ) : (
                      <TableRow>
                        <TableCell colSpan={7} className="text-center text-muted-foreground">
                          取引履歴がありません
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>

        {/* 配当金履歴 */}
        <Card>
          <CardHeader>
            <CardTitle>配当金履歴</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoadingDividends ? (
              <div className="space-y-2">
                {[...Array(3)].map((_, i) => (
                  // biome-ignore lint/suspicious/noArrayIndexKey: Static skeleton loading elements
                  <div key={`skeleton-${i}`} className="h-12 animate-pulse rounded bg-muted" />
                ))}
              </div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>支払日</TableHead>
                      <TableHead className="text-right">保有株数</TableHead>
                      <TableHead className="text-right">配当金額</TableHead>
                      <TableHead className="text-right">税金</TableHead>
                      <TableHead className="text-right">手数料</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {dividends && dividends.length > 0 ? (
                      dividends.map((dividend) => (
                        <TableRow key={dividend.dividend_id}>
                          <TableCell>{formatDate(dividend.payment_date)}</TableCell>
                          <TableCell className="text-right">
                            {Number(dividend.shares_owned).toLocaleString()}株
                          </TableCell>
                          <TableCell className="text-right">
                            {formatCurrency(dividend.total_amount)}
                          </TableCell>
                          <TableCell className="text-right">
                            {dividend.tax ? formatCurrency(dividend.tax) : "-"}
                          </TableCell>
                          <TableCell className="text-right">
                            {dividend.fee ? formatCurrency(dividend.fee) : "-"}
                          </TableCell>
                        </TableRow>
                      ))
                    ) : (
                      <TableRow>
                        <TableCell colSpan={5} className="text-center text-muted-foreground">
                          配当金履歴がありません
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>
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
