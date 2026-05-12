import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { TablePagination } from "@/components/ui/table-pagination"
import { useTableSort } from "@/hooks/use-table-sort"
import type { PortfolioHistoryItem } from "@/lib/api/types"
import { formatCurrency, formatDate } from "@/lib/format"
import { usePagination } from "@/lib/hooks/use-pagination"

interface PortfolioHistoryTableProps {
  history: PortfolioHistoryItem[] | undefined
  isLoading: boolean
}

type SortKey = "date" | "total_cost" | "total_market_value" | "total_unrealized_pl" | "total_pl"

const PAGE_SIZE = 20

export function PortfolioHistoryTable({ history, isLoading }: PortfolioHistoryTableProps) {
  const {
    sortKey,
    sortDirection,
    handleSort: baseSortHandler,
    getSortIcon,
  } = useTableSort<SortKey>({
    defaultSortKey: "date",
    defaultSortDirection: "desc",
  })

  const sortedHistory = history?.slice().sort((a, b) => {
    let aValue: number = 0
    let bValue: number = 0

    switch (sortKey) {
      case "date":
        aValue = new Date(a.date).getTime()
        bValue = new Date(b.date).getTime()
        break
      case "total_cost":
        aValue = a.total_cost
        bValue = b.total_cost
        break
      case "total_market_value":
        aValue = a.total_market_value
        bValue = b.total_market_value
        break
      case "total_unrealized_pl":
        aValue = a.total_unrealized_pl
        bValue = b.total_unrealized_pl
        break
      case "total_pl":
        aValue = a.total_pl
        bValue = b.total_pl
        break
    }

    return sortDirection === "asc" ? aValue - bValue : bValue - aValue
  })

  const { currentPage, totalPages, paginatedData, handlePageChange, hasNextPage, hasPreviousPage } =
    usePagination(sortedHistory, PAGE_SIZE)

  const handleSort = (key: SortKey) => {
    baseSortHandler(key)
    handlePageChange(1)
  }

  const formatPercentage = (value: number) => {
    const sign = value >= 0 ? "+" : ""
    return `${sign}${value.toFixed(2)}%`
  }

  const getPLColor = (value: number) => {
    if (value > 0) return "text-success"
    if (value < 0) return "text-destructive"
    return ""
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>資産推移</CardTitle>
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
                    className="cursor-pointer select-none text-right"
                    onClick={() => handleSort("date")}
                  >
                    <div className="flex items-center justify-end">
                      日付
                      {getSortIcon("date")}
                    </div>
                  </TableHead>
                  <TableHead
                    className="cursor-pointer select-none text-right"
                    onClick={() => handleSort("total_cost")}
                  >
                    <div className="flex items-center justify-end">
                      取得価額
                      {getSortIcon("total_cost")}
                    </div>
                  </TableHead>
                  <TableHead
                    className="cursor-pointer select-none text-right"
                    onClick={() => handleSort("total_market_value")}
                  >
                    <div className="flex items-center justify-end">
                      時価評価額
                      {getSortIcon("total_market_value")}
                    </div>
                  </TableHead>
                  <TableHead
                    className="cursor-pointer select-none text-right"
                    onClick={() => handleSort("total_unrealized_pl")}
                  >
                    <div className="flex items-center justify-end">
                      評価損益
                      {getSortIcon("total_unrealized_pl")}
                    </div>
                  </TableHead>
                  <TableHead className="text-right">評価損益率</TableHead>
                  <TableHead className="text-right">実現損益</TableHead>
                  <TableHead className="text-right">配当金</TableHead>
                  <TableHead
                    className="cursor-pointer select-none text-right"
                    onClick={() => handleSort("total_pl")}
                  >
                    <div className="flex items-center justify-end">
                      全体損益
                      {getSortIcon("total_pl")}
                    </div>
                  </TableHead>
                  <TableHead className="text-right">全体損益率</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {paginatedData && paginatedData.length > 0 ? (
                  paginatedData.map((item) => (
                    <TableRow key={item.date}>
                      <TableCell className="text-right">{formatDate(item.date)}</TableCell>
                      <TableCell className="text-right">
                        {formatCurrency(item.total_cost.toString())}
                      </TableCell>
                      <TableCell className="text-right">
                        {formatCurrency(item.total_market_value.toString())}
                      </TableCell>
                      <TableCell className={`text-right ${getPLColor(item.total_unrealized_pl)}`}>
                        {formatCurrency(item.total_unrealized_pl.toString())}
                      </TableCell>
                      <TableCell className={`text-right ${getPLColor(item.total_unrealized_pl_percentage)}`}>
                        {formatPercentage(item.total_unrealized_pl_percentage)}
                      </TableCell>
                      <TableCell className="text-right">
                        {formatCurrency(item.total_realized_pl.toString())}
                      </TableCell>
                      <TableCell className="text-right">
                        {formatCurrency(item.total_dividend.toString())}
                      </TableCell>
                      <TableCell className={`text-right ${getPLColor(item.total_pl)}`}>
                        {formatCurrency(item.total_pl.toString())}
                      </TableCell>
                      <TableCell className={`text-right ${getPLColor(item.total_pl_percentage)}`}>
                        {formatPercentage(item.total_pl_percentage)}
                      </TableCell>
                    </TableRow>
                  ))
                ) : (
                  <TableRow>
                    <TableCell colSpan={9} className="text-center text-muted-foreground">
                      履歴がありません
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
