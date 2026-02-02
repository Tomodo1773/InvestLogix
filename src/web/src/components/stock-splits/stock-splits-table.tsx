import { ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react"
import { useState } from "react"
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
import type { StockSplit } from "@/lib/api/types"
import { formatDate } from "@/lib/format"
import { usePagination } from "@/lib/hooks/use-pagination"

interface StockSplitsTableProps {
  stockSplits: StockSplit[] | undefined
  isLoading: boolean
}

type SortKey = "symbol" | "stock_name" | "split_date" | "split_ratio"
type SortDirection = "asc" | "desc"

const PAGE_SIZE = 20

export function StockSplitsTable({ stockSplits, isLoading }: StockSplitsTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>("split_date")
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc")

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDirection(sortDirection === "asc" ? "desc" : "asc")
    } else {
      setSortKey(key)
      setSortDirection("desc")
    }
    handlePageChange(1)
  }

  const getSortIcon = (key: SortKey) => {
    if (sortKey !== key) {
      return <ArrowUpDown className="ml-1 h-4 w-4" />
    }
    return sortDirection === "asc" ? (
      <ArrowUp className="ml-1 h-4 w-4" />
    ) : (
      <ArrowDown className="ml-1 h-4 w-4" />
    )
  }

  const sortedStockSplits = stockSplits?.sort((a, b) => {
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

  const formatSplitRatio = (ratio: string) => {
    const numRatio = Number(ratio)
    if (Number.isNaN(numRatio)) return ratio
    return `${numRatio}:1 分割`
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
                    onClick={() => handleSort("split_date")}
                  >
                    <div className="flex items-center justify-end">
                      分割日
                      {getSortIcon("split_date")}
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
                        <TableCell>
                          <div className="font-medium">{stockSplit.symbol}</div>
                        </TableCell>
                        <TableCell>
                          <div className="text-sm text-muted-foreground">{stockSplit.stock_name || "-"}</div>
                        </TableCell>
                        <TableCell className="text-right">{formatDate(stockSplit.split_date)}</TableCell>
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
