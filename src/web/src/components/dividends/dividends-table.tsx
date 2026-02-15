import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { useTableSort } from "@/hooks/use-table-sort"
import type { Dividend } from "@/lib/api/types"
import { formatCurrency } from "@/lib/format"
import { usePagination } from "@/lib/hooks/use-pagination"

interface DividendsTableProps {
  dividends: Dividend[] | undefined
  isLoading: boolean
}

type SortKey = "symbol" | "payment_date" | "total_amount"

const PAGE_SIZE = 20

export function DividendsTable({ dividends, isLoading }: DividendsTableProps) {
  const {
    sortKey,
    sortDirection,
    handleSort: baseSortHandler,
    getSortIcon,
  } = useTableSort<SortKey>({
    defaultSortKey: "payment_date",
    defaultSortDirection: "desc",
  })

  const sortedDividends = dividends?.sort((a, b) => {
    let aValue: number | string = 0
    let bValue: number | string = 0

    switch (sortKey) {
      case "symbol":
        aValue = a.symbol
        bValue = b.symbol
        break
      case "payment_date":
        aValue = new Date(a.payment_date).getTime()
        bValue = new Date(b.payment_date).getTime()
        break
      case "total_amount":
        aValue = a.total_amount
        bValue = b.total_amount
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
    usePagination(sortedDividends, PAGE_SIZE)

  const handleSort = (key: SortKey) => {
    baseSortHandler(key)
    handlePageChange(1)
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleDateString("ja-JP", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    })
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>配当金履歴</CardTitle>
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
                  <TableHead className="cursor-pointer select-none" onClick={() => handleSort("symbol")}>
                    <div className="flex items-center">
                      銘柄名/コード
                      {getSortIcon("symbol")}
                    </div>
                  </TableHead>
                  <TableHead
                    className="cursor-pointer select-none text-right"
                    onClick={() => handleSort("payment_date")}
                  >
                    <div className="flex items-center justify-end">
                      支払日
                      {getSortIcon("payment_date")}
                    </div>
                  </TableHead>
                  <TableHead className="text-right">株数</TableHead>
                  <TableHead
                    className="cursor-pointer select-none text-right"
                    onClick={() => handleSort("total_amount")}
                  >
                    <div className="flex items-center justify-end">
                      配当金額
                      {getSortIcon("total_amount")}
                    </div>
                  </TableHead>
                  <TableHead className="text-right">税金</TableHead>
                  <TableHead className="text-right">手数料</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {paginatedData && paginatedData.length > 0 ? (
                  paginatedData.map((dividend) => {
                    return (
                      <TableRow key={dividend.dividend_id}>
                        <TableCell>
                          <div>
                            <div className="font-medium">{dividend.stock_name || dividend.symbol}</div>
                            <div className="text-sm text-muted-foreground">{dividend.symbol}</div>
                          </div>
                        </TableCell>
                        <TableCell className="text-right">{formatDate(dividend.payment_date)}</TableCell>
                        <TableCell className="text-right">{dividend.shares_owned.toLocaleString()}</TableCell>
                        <TableCell className="text-right font-medium text-[#4CAF50]">
                          {formatCurrency(dividend.total_amount)}
                        </TableCell>
                        <TableCell className="text-right">
                          {dividend.tax ? formatCurrency(dividend.tax) : "-"}
                        </TableCell>
                        <TableCell className="text-right">
                          {dividend.fee ? formatCurrency(dividend.fee) : "-"}
                        </TableCell>
                      </TableRow>
                    )
                  })
                ) : (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center text-muted-foreground">
                      配当金履歴がありません
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
            {totalPages > 1 && (
              <div className="mt-4 flex justify-center">
                <Pagination>
                  <PaginationContent>
                    <PaginationItem>
                      <PaginationPrevious
                        onClick={() => handlePageChange(currentPage - 1)}
                        className={!hasPreviousPage ? "pointer-events-none opacity-50" : "cursor-pointer"}
                      />
                    </PaginationItem>

                    {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => {
                      // 最初、最後、現在ページの前後1ページのみ表示
                      if (
                        page === 1 ||
                        page === totalPages ||
                        (page >= currentPage - 1 && page <= currentPage + 1)
                      ) {
                        return (
                          <PaginationItem key={page}>
                            <PaginationLink
                              onClick={() => handlePageChange(page)}
                              isActive={currentPage === page}
                              className="cursor-pointer"
                            >
                              {page}
                            </PaginationLink>
                          </PaginationItem>
                        )
                      }
                      // 省略記号
                      if (page === currentPage - 2 || page === currentPage + 2) {
                        return <PaginationEllipsis key={page} />
                      }
                      return null
                    })}

                    <PaginationItem>
                      <PaginationNext
                        onClick={() => handlePageChange(currentPage + 1)}
                        className={!hasNextPage ? "pointer-events-none opacity-50" : "cursor-pointer"}
                      />
                    </PaginationItem>
                  </PaginationContent>
                </Pagination>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
