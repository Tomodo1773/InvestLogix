import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import type { TransactionWithPL } from "@/lib/api/types"
import { formatCurrency, formatDate, formatPercent, getPLColorClass } from "@/lib/format"

interface HoldingTransactionsSectionProps {
  transactions: TransactionWithPL[] | undefined
  isLoading: boolean
}

export function HoldingTransactionsSection({ transactions, isLoading }: HoldingTransactionsSectionProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>取引履歴</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
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
                        ? transaction.unrealized_pl_percentage
                        : null
                    const plColor = plValue !== null ? getPLColorClass(plValue) : ""

                    return (
                      <TableRow key={transaction.transaction_id}>
                        <TableCell>{formatDate(transaction.transaction_date)}</TableCell>
                        <TableCell>
                          <span
                            className={
                              transaction.transaction_type === "buy" ? "text-success" : "text-destructive"
                            }
                          >
                            {transaction.transaction_type === "buy" ? "買付" : "売却"}
                          </span>
                        </TableCell>
                        <TableCell className="text-right">{displayQuantity.toLocaleString()}</TableCell>
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
  )
}
