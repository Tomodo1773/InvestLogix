import { Link } from "react-router"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { useTableSort } from "@/hooks/use-table-sort"
import type { Holding } from "@/lib/api/types"
import { formatCurrency, formatPercent } from "@/lib/format"

interface HoldingsTableProps {
  holdings: Holding[] | undefined
  isLoading: boolean
}

type SortKey = "symbol" | "quantity" | "current_price" | "market_value" | "total_pl" | "total_pl_percentage"

export function HoldingsTable({ holdings, isLoading }: HoldingsTableProps) {
  const { sortKey, sortDirection, handleSort, getSortIcon } = useTableSort<SortKey>({
    defaultSortKey: "market_value",
    defaultSortDirection: "desc",
  })

  const sortedHoldings = holdings
    ?.filter((holding) => holding.quantity > 0)
    .sort((a, b) => {
      let aValue: number | string = 0
      let bValue: number | string = 0

      switch (sortKey) {
        case "symbol":
          aValue = a.symbol
          bValue = b.symbol
          break
        case "quantity":
          aValue = a.quantity
          bValue = b.quantity
          break
        case "current_price":
          aValue = a.current_price ?? 0
          bValue = b.current_price ?? 0
          break
        case "market_value":
          aValue = a.market_value ?? 0
          bValue = b.market_value ?? 0
          break
        case "total_pl":
          aValue = a.total_pl ?? 0
          bValue = b.total_pl ?? 0
          break
        case "total_pl_percentage":
          aValue = a.total_pl_percentage ?? 0
          bValue = b.total_pl_percentage ?? 0
          break
      }

      if (typeof aValue === "string" && typeof bValue === "string") {
        return sortDirection === "asc" ? aValue.localeCompare(bValue) : bValue.localeCompare(aValue)
      }

      return sortDirection === "asc"
        ? (aValue as number) - (bValue as number)
        : (bValue as number) - (aValue as number)
    })

  return (
    <Card>
      <CardHeader>
        <CardTitle>銘柄別保有状況</CardTitle>
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
                    onClick={() => handleSort("quantity")}
                  >
                    <div className="flex items-center justify-end">
                      株数
                      {getSortIcon("quantity")}
                    </div>
                  </TableHead>
                  <TableHead
                    className="cursor-pointer select-none text-right"
                    onClick={() => handleSort("current_price")}
                  >
                    <div className="flex items-center justify-end">
                      前日終値
                      {getSortIcon("current_price")}
                    </div>
                  </TableHead>
                  <TableHead
                    className="cursor-pointer select-none text-right"
                    onClick={() => handleSort("market_value")}
                  >
                    <div className="flex items-center justify-end">
                      評価額
                      {getSortIcon("market_value")}
                    </div>
                  </TableHead>
                  <TableHead
                    className="cursor-pointer select-none text-right"
                    onClick={() => handleSort("total_pl")}
                  >
                    <div className="flex items-center justify-end">
                      損益
                      {getSortIcon("total_pl")}
                    </div>
                  </TableHead>
                  <TableHead
                    className="cursor-pointer select-none text-right"
                    onClick={() => handleSort("total_pl_percentage")}
                  >
                    <div className="flex items-center justify-end">
                      損益%
                      {getSortIcon("total_pl_percentage")}
                    </div>
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sortedHoldings && sortedHoldings.length > 0 ? (
                  sortedHoldings.map((holding) => {
                    const plValue = holding.total_pl ?? 0
                    const plColor = plValue >= 0 ? "text-[#4CAF50]" : "text-destructive"

                    return (
                      <TableRow key={holding.symbol}>
                        <TableCell>
                          <Link to={`/holdings/${holding.symbol}`}>
                            <div className="cursor-pointer hover:opacity-80">
                              <div className="font-medium hover:underline">
                                {holding.stock_name || holding.symbol}
                              </div>
                              <div className="text-sm text-muted-foreground">{holding.symbol}</div>
                            </div>
                          </Link>
                        </TableCell>
                        <TableCell className="text-right">{holding.quantity.toLocaleString()}</TableCell>
                        <TableCell className="text-right">
                          {holding.current_price ? formatCurrency(holding.current_price) : "-"}
                        </TableCell>
                        <TableCell className="text-right">
                          {holding.market_value ? formatCurrency(holding.market_value) : "-"}
                        </TableCell>
                        <TableCell className={`text-right font-medium ${plColor}`}>
                          {holding.total_pl ? formatCurrency(holding.total_pl) : "-"}
                        </TableCell>
                        <TableCell className={`text-right font-medium ${plColor}`}>
                          {holding.total_pl_percentage ? formatPercent(holding.total_pl_percentage) : "-"}
                        </TableCell>
                      </TableRow>
                    )
                  })
                ) : (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center text-muted-foreground">
                      保有銘柄がありません
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
