import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { TablePagination } from "@/components/ui/table-pagination"
import { useTableSort } from "@/hooks/use-table-sort"
import type { StockSplit } from "@/lib/api/types"
import { formatDate } from "@/lib/format"
import { usePagination } from "@/lib/hooks/use-pagination"

interface StockSplitsTableProps {
  stockSplits: StockSplit[] | undefined
  isLoading: boolean
}

type SortKey = "symbol" | "stock_name" | "split_date" | "split_ratio"

const PAGE_SIZE = 20

export function StockSplitsTable({ stockSplits, isLoading }: StockSplitsTableProps) {
  const {
    sortKey,
    sortDirection,
    handleSort: baseSortHandler,
    getSortIcon,
  } = useTableSort<SortKey>({
    defaultSortKey: "split_date",
    defaultSortDirection: "desc",
  })

  const sortedStockSplits = stockSplits?.slice().sort((a, b) => {
    let aValue: number | string = 0
    let bValue: number | string = 0

    switch (sortKey) {
      case "symbol":
        aValue = a.symbol
        bValue = b.symbol
        break
      case "stock_name":
        aValue = a.stock_name || ""
        bValue = b.stock_name || ""
        break
      case "split_date":
        aValue = new Date(a.split_date).getTime()
        bValue = new Date(b.split_date).getTime()
        break
      case "split_ratio":
        aValue = Number(a.split_ratio)
        bValue = Number(b.split_ratio)
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
    usePagination(sortedStockSplits, PAGE_SIZE)

  const handleSort = (key: SortKey) => {
    baseSortHandler(key)
    handlePageChange(1)
  }

  const formatSplitRatio = (ratio: number) => {
    if (Number.isNaN(ratio)) return String(ratio)
    return `${ratio}:1 分割`
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>株式分割履歴</CardTitle>
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
                  <TableHead className="cursor-pointer select-none" onClick={() => handleSort("split_date")}>
                    <div className="flex items-center">
                      分割日
                      {getSortIcon("split_date")}
                    </div>
                  </TableHead>
                  <TableHead className="cursor-pointer select-none" onClick={() => handleSort("symbol")}>
                    <div className="flex items-center">
                      銘柄コード
                      {getSortIcon("symbol")}
                    </div>
                  </TableHead>
                  <TableHead className="cursor-pointer select-none" onClick={() => handleSort("stock_name")}>
                    <div className="flex items-center">
                      銘柄名
                      {getSortIcon("stock_name")}
                    </div>
                  </TableHead>
                  <TableHead
                    className="cursor-pointer select-none text-right"
                    onClick={() => handleSort("split_ratio")}
                  >
                    <div className="flex items-center justify-end">
                      分割比率
                      {getSortIcon("split_ratio")}
                    </div>
                  </TableHead>
                  <TableHead className="text-right">登録日</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {paginatedData && paginatedData.length > 0 ? (
                  paginatedData.map((stockSplit) => {
                    return (
                      <TableRow key={stockSplit.split_id}>
                        <TableCell>{formatDate(stockSplit.split_date)}</TableCell>
                        <TableCell>
                          <div className="font-medium">{stockSplit.symbol}</div>
                        </TableCell>
                        <TableCell>
                          <div className="text-sm text-muted-foreground">{stockSplit.stock_name || "-"}</div>
                        </TableCell>
                        <TableCell className="text-right font-medium">
                          {formatSplitRatio(stockSplit.split_ratio)}
                        </TableCell>
                        <TableCell className="text-right text-sm text-muted-foreground">
                          {formatDate(stockSplit.created_at)}
                        </TableCell>
                      </TableRow>
                    )
                  })
                ) : (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center text-muted-foreground">
                      株式分割履歴がありません
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
