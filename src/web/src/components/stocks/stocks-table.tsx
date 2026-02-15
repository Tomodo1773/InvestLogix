import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { useTableSort } from "@/hooks/use-table-sort"
import type { Stock } from "@/lib/api/types"
import { formatDate } from "@/lib/format"
import { usePagination } from "@/lib/hooks/use-pagination"

interface StocksTableProps {
  stocks: Stock[] | undefined
  isLoading: boolean
}

type SortKey = "symbol" | "name" | "market" | "security_type" | "currency" | "last_updated"

const ITEMS_PER_PAGE = 20

const securityTypeLabel: Record<string, string> = {
  STOCK: "株式",
  ETF: "ETF",
  REIT: "REIT",
  FUND: "投資信託",
}

export function StocksTable({ stocks, isLoading }: StocksTableProps) {
  const { sortKey, sortDirection, handleSort, getSortIcon } = useTableSort<SortKey>({
    defaultSortKey: "symbol",
    defaultSortDirection: "asc",
  })

  const sortedStocks = stocks?.slice().sort((a, b) => {
    let aValue: string | number = ""
    let bValue: string | number = ""

    switch (sortKey) {
      case "symbol":
        aValue = a.symbol
        bValue = b.symbol
        break
      case "name":
        aValue = a.name
        bValue = b.name
        break
      case "market":
        aValue = a.market
        bValue = b.market
        break
      case "security_type":
        aValue = a.security_type
        bValue = b.security_type
        break
      case "currency":
        aValue = a.currency
        bValue = b.currency
        break
      case "last_updated":
        aValue = new Date(a.last_updated).getTime()
        bValue = new Date(b.last_updated).getTime()
        break
    }

    if (typeof aValue === "string" && typeof bValue === "string") {
      return sortDirection === "asc" ? aValue.localeCompare(bValue) : bValue.localeCompare(aValue)
    }

    return sortDirection === "asc"
      ? (aValue as number) - (bValue as number)
      : (bValue as number) - (aValue as number)
  })

  const { paginatedData, currentPage, totalPages, handlePageChange, hasNextPage, hasPreviousPage } =
    usePagination(sortedStocks, ITEMS_PER_PAGE)

  return (
    <Card>
      <CardHeader>
        <CardTitle>銘柄マスター</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-2">
            {[...Array(5)].map((_, i) => (
              // biome-ignore lint/suspicious/noArrayIndexKey: Static skeleton loading elements
              <div key={`skeleton-${i}`} className="h-12 animate-pulse rounded bg-muted" />
            ))}
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="cursor-pointer select-none" onClick={() => handleSort("symbol")}>
                      <div className="flex items-center">
                        シンボル
                        {getSortIcon("symbol")}
                      </div>
                    </TableHead>
                    <TableHead className="cursor-pointer select-none" onClick={() => handleSort("name")}>
                      <div className="flex items-center">
                        銘柄名
                        {getSortIcon("name")}
                      </div>
                    </TableHead>
                    <TableHead>英語名</TableHead>
                    <TableHead
                      className="cursor-pointer select-none text-center"
                      onClick={() => handleSort("market")}
                    >
                      <div className="flex items-center justify-center">
                        市場
                        {getSortIcon("market")}
                      </div>
                    </TableHead>
                    <TableHead
                      className="cursor-pointer select-none text-center"
                      onClick={() => handleSort("security_type")}
                    >
                      <div className="flex items-center justify-center">
                        種別
                        {getSortIcon("security_type")}
                      </div>
                    </TableHead>
                    <TableHead
                      className="cursor-pointer select-none text-center"
                      onClick={() => handleSort("currency")}
                    >
                      <div className="flex items-center justify-center">
                        通貨
                        {getSortIcon("currency")}
                      </div>
                    </TableHead>
                    <TableHead
                      className="cursor-pointer select-none text-right"
                      onClick={() => handleSort("last_updated")}
                    >
                      <div className="flex items-center justify-end">
                        最終更新
                        {getSortIcon("last_updated")}
                      </div>
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {paginatedData && paginatedData.length > 0 ? (
                    paginatedData.map((stock) => (
                      <TableRow key={stock.symbol}>
                        <TableCell className="font-medium">{stock.symbol}</TableCell>
                        <TableCell>{stock.name}</TableCell>
                        <TableCell className="text-muted-foreground">{stock.name_en || "-"}</TableCell>
                        <TableCell className="text-center">{stock.market}</TableCell>
                        <TableCell className="text-center">
                          {securityTypeLabel[stock.security_type] || stock.security_type}
                        </TableCell>
                        <TableCell className="text-center">{stock.currency}</TableCell>
                        <TableCell className="text-right">{formatDate(stock.last_updated)}</TableCell>
                      </TableRow>
                    ))
                  ) : (
                    <TableRow>
                      <TableCell colSpan={7} className="text-center text-muted-foreground">
                        登録銘柄がありません
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </div>
            {paginatedData && paginatedData.length > 0 && (
              <div className="mt-4 flex items-center justify-between">
                <div className="text-sm text-muted-foreground">
                  {sortedStocks?.length || 0} 件中 {(currentPage - 1) * ITEMS_PER_PAGE + 1} -{" "}
                  {Math.min(currentPage * ITEMS_PER_PAGE, sortedStocks?.length || 0)} 件を表示
                </div>
                <div className="flex gap-2">
                  <button
                    type="button"
                    className="rounded border px-3 py-1 text-sm disabled:cursor-not-allowed disabled:opacity-50"
                    onClick={() => handlePageChange(currentPage - 1)}
                    disabled={!hasPreviousPage}
                  >
                    前へ
                  </button>
                  <div className="flex items-center px-3 text-sm">
                    {currentPage} / {totalPages}
                  </div>
                  <button
                    type="button"
                    className="rounded border px-3 py-1 text-sm disabled:cursor-not-allowed disabled:opacity-50"
                    onClick={() => handlePageChange(currentPage + 1)}
                    disabled={!hasNextPage}
                  >
                    次へ
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  )
}
