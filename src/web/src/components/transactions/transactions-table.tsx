import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { TablePagination } from "@/components/ui/table-pagination"
import { useTableSort } from "@/hooks/use-table-sort"
import type { Transaction } from "@/lib/api/types"
import { formatCurrency, formatDate } from "@/lib/format"
import { usePagination } from "@/lib/hooks/use-pagination"

interface TransactionsTableProps {
  transactions: Transaction[] | undefined
  isLoading: boolean
}

type SortKey = "symbol" | "transaction_date" | "quantity" | "price" | "total_amount"

const PAGE_SIZE = 20

export function TransactionsTable({ transactions, isLoading }: TransactionsTableProps) {
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
        aValue = a.quantity
        bValue = b.quantity
        break
      case "price":
        aValue = a.price
        bValue = b.price
        break
      case "total_amount":
        aValue = a.quantity * a.price
        bValue = b.quantity * b.price
        break
    }

    if (typeof aValue === "string" && typeof bValue === "string") {
      return sortDirection === "asc" ? aValue.localeCompare(bValue) : bValue.localeCompare(aValue)
    }

    return sortDirection === "asc"
      ? (aValue as number) - (bValue as number)
      : (bValue as number) - (aValue as number)
  })

  const { currentPage, totalPages, paginatedData, handlePageChange, hasNextPage, hasPreviousPage } =
    usePagination(sortedTransactions, PAGE_SIZE)

  const handleSort = (key: SortKey) => {
    baseSortHandler(key)
    handlePageChange(1)
  }

  const getAccountTypeLabel = (accountType: string) => {
    // バックエンドから返される値をそのまま表示
    return accountType
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>取引履歴</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-2">
            {[...Array(20)].map((_, i) => (
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
                  <TableHead className="cursor-pointer select-none" onClick={() => handleSort("symbol")}>
                    <div className="flex items-center">
                      銘柄名/コード
                      {getSortIcon("symbol")}
                    </div>
                  </TableHead>
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
                </TableRow>
              </TableHeader>
              <TableBody>
                {paginatedData && paginatedData.length > 0 ? (
                  paginatedData.map((transaction) => {
                    const totalAmount = transaction.quantity * transaction.price
                    const isBuy = transaction.transaction_type === "buy"

                    return (
                      <TableRow key={transaction.transaction_id}>
                        <TableCell>{formatDate(transaction.transaction_date)}</TableCell>
                        <TableCell>
                          <div>
                            <div className="font-medium">{transaction.stock_name || transaction.symbol}</div>
                            <div className="text-sm text-muted-foreground">{transaction.symbol}</div>
                          </div>
                        </TableCell>
                        <TableCell>
                          <span
                            className={`inline-flex items-center rounded-full px-2 py-1 text-xs font-medium ${
                              isBuy ? "bg-[#4CAF50]/10 text-[#4CAF50]" : "bg-destructive/10 text-destructive"
                            }`}
                          >
                            {isBuy ? "買付" : "売却"}
                          </span>
                        </TableCell>
                        <TableCell>{getAccountTypeLabel(transaction.account_type)}</TableCell>
                        <TableCell className="text-right">{transaction.quantity.toLocaleString()}</TableCell>
                        <TableCell className="text-right">{formatCurrency(transaction.price)}</TableCell>
                        <TableCell className="text-right">{formatCurrency(totalAmount)}</TableCell>
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
