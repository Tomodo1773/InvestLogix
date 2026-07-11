import { useRef } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { TablePagination } from "@/components/ui/table-pagination"
import { useTableSort } from "@/hooks/use-table-sort"
import type { Transaction, TransactionWithPL } from "@/lib/api/types"
import { formatCurrency, formatDate, formatPercent, getPLColorClass } from "@/lib/format"
import { usePagination } from "@/lib/hooks/use-pagination"

type TransactionsTableMode = "all" | "holding"

interface TransactionsTableProps {
  transactions: Transaction[] | undefined
  isLoading: boolean
  mode?: TransactionsTableMode
}

type SortKey = "symbol" | "transaction_date" | "quantity" | "price" | "total_amount"

const PAGE_SIZE = 20

function isTransactionWithPL(transaction: Transaction): transaction is TransactionWithPL {
  return "unrealized_pl_percentage" in transaction
}

function getDisplayValues(transaction: Transaction, mode: TransactionsTableMode) {
  const quantity =
    mode === "holding" ? (transaction.adjusted_quantity ?? transaction.quantity) : transaction.quantity
  const price = mode === "holding" ? (transaction.adjusted_price ?? transaction.price) : transaction.price

  return { quantity, price, totalAmount: quantity * price }
}

export function TransactionsTable({ transactions, isLoading, mode = "all" }: TransactionsTableProps) {
  const tableRef = useRef<HTMLDivElement>(null)
  const {
    sortKey,
    sortDirection,
    handleSort: baseSortHandler,
    getSortIcon,
  } = useTableSort<SortKey>({
    defaultSortKey: "transaction_date",
    defaultSortDirection: "desc",
  })

  const sortedTransactions = transactions?.slice().sort((a, b) => {
    let aValue: number | string = 0
    let bValue: number | string = 0

    switch (sortKey) {
      case "symbol":
        aValue = a.symbol
        bValue = b.symbol
        break
      case "transaction_date":
        aValue = new Date(a.transaction_date).getTime()
        bValue = new Date(b.transaction_date).getTime()
        break
      case "quantity":
        aValue = getDisplayValues(a, mode).quantity
        bValue = getDisplayValues(b, mode).quantity
        break
      case "price":
        aValue = getDisplayValues(a, mode).price
        bValue = getDisplayValues(b, mode).price
        break
      case "total_amount":
        aValue = getDisplayValues(a, mode).totalAmount
        bValue = getDisplayValues(b, mode).totalAmount
        break
    }

    if (typeof aValue === "string" && typeof bValue === "string") {
      return sortDirection === "asc" ? aValue.localeCompare(bValue) : bValue.localeCompare(aValue)
    }

    return sortDirection === "asc"
      ? (aValue as number) - (bValue as number)
      : (bValue as number) - (aValue as number)
  })

  const {
    currentPage,
    totalPages,
    paginatedData,
    handlePageChange: changePage,
    hasNextPage,
    hasPreviousPage,
  } = usePagination(sortedTransactions, PAGE_SIZE, { scrollToTop: mode === "all" })

  const handlePageChange = (page: number) => {
    if (page < 1 || page > totalPages) return

    changePage(page)
    if (mode === "holding") {
      tableRef.current?.scrollIntoView({ block: "start" })
    }
  }

  const handleSort = (key: SortKey) => {
    baseSortHandler(key)
    handlePageChange(1)
  }

  const columnCount = mode === "holding" ? 9 : 7
  const skeletonCount = mode === "holding" ? 3 : PAGE_SIZE

  return (
    <Card ref={tableRef}>
      <CardHeader>
        <CardTitle>取引履歴</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-2">
            {[...Array(skeletonCount)].map((_, i) => (
              // biome-ignore lint/suspicious/noArrayIndexKey: Static skeleton loading elements
              <div key={`skeleton-${i}`} className="h-12 animate-pulse rounded bg-muted" />
            ))}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead
                    className="cursor-pointer select-none"
                    onClick={() => handleSort("transaction_date")}
                  >
                    <div className="flex items-center">
                      日付
                      {getSortIcon("transaction_date")}
                    </div>
                  </TableHead>
                  {mode === "all" ? (
                    <TableHead className="cursor-pointer select-none" onClick={() => handleSort("symbol")}>
                      <div className="flex items-center">
                        銘柄名/コード
                        {getSortIcon("symbol")}
                      </div>
                    </TableHead>
                  ) : null}
                  <TableHead>取引種別</TableHead>
                  <TableHead>口座</TableHead>
                  <TableHead
                    className="cursor-pointer select-none text-right"
                    onClick={() => handleSort("quantity")}
                  >
                    <div className="flex items-center justify-end">
                      数量
                      {getSortIcon("quantity")}
                    </div>
                  </TableHead>
                  <TableHead
                    className="cursor-pointer select-none text-right"
                    onClick={() => handleSort("price")}
                  >
                    <div className="flex items-center justify-end">
                      単価
                      {getSortIcon("price")}
                    </div>
                  </TableHead>
                  <TableHead
                    className="cursor-pointer select-none text-right"
                    onClick={() => handleSort("total_amount")}
                  >
                    <div className="flex items-center justify-end">
                      金額
                      {getSortIcon("total_amount")}
                    </div>
                  </TableHead>
                  {mode === "holding" ? (
                    <>
                      <TableHead className="text-right">手数料</TableHead>
                      <TableHead className="text-right">税金</TableHead>
                      <TableHead className="text-right">損益率</TableHead>
                    </>
                  ) : null}
                </TableRow>
              </TableHeader>
              <TableBody>
                {paginatedData && paginatedData.length > 0 ? (
                  paginatedData.map((transaction) => {
                    const { quantity, price, totalAmount } = getDisplayValues(transaction, mode)
                    const isBuy = transaction.transaction_type === "buy"
                    const unrealizedPlPercentage = isTransactionWithPL(transaction)
                      ? transaction.unrealized_pl_percentage
                      : null

                    return (
                      <TableRow key={transaction.transaction_id}>
                        <TableCell>{formatDate(transaction.transaction_date)}</TableCell>
                        {mode === "all" ? (
                          <TableCell>
                            <div>
                              <div className="font-medium">
                                {transaction.stock_name || transaction.symbol}
                              </div>
                              <div className="text-sm text-muted-foreground">{transaction.symbol}</div>
                            </div>
                          </TableCell>
                        ) : null}
                        <TableCell>
                          <span
                            className={`inline-flex items-center rounded-full px-2 py-1 text-xs font-medium ${
                              isBuy ? "bg-success/10 text-success" : "bg-destructive/10 text-destructive"
                            }`}
                          >
                            {isBuy ? "買付" : "売却"}
                          </span>
                        </TableCell>
                        <TableCell>{transaction.account_type}</TableCell>
                        <TableCell className="text-right">{quantity.toLocaleString()}</TableCell>
                        <TableCell className="text-right">{formatCurrency(price)}</TableCell>
                        <TableCell className="text-right">{formatCurrency(totalAmount)}</TableCell>
                        {mode === "holding" ? (
                          <>
                            <TableCell className="text-right">{formatCurrency(transaction.fee)}</TableCell>
                            <TableCell className="text-right">{formatCurrency(transaction.tax)}</TableCell>
                            <TableCell
                              className={`text-right font-medium ${getPLColorClass(unrealizedPlPercentage)}`}
                            >
                              {isBuy && unrealizedPlPercentage !== null
                                ? formatPercent(unrealizedPlPercentage)
                                : "-"}
                            </TableCell>
                          </>
                        ) : null}
                      </TableRow>
                    )
                  })
                ) : (
                  <TableRow>
                    <TableCell colSpan={columnCount} className="text-center text-muted-foreground">
                      取引履歴がありません
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
            <TablePagination
              currentPage={currentPage}
              totalPages={totalPages}
              hasNextPage={hasNextPage}
              hasPreviousPage={hasPreviousPage}
              onPageChange={handlePageChange}
            />
          </div>
        )}
      </CardContent>
    </Card>
  )
}
