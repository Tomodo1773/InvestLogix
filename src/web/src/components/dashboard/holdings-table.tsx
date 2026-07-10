import { CircleCheck, CircleMinus } from "lucide-react"
import { Link } from "react-router"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { useTableSort } from "@/hooks/use-table-sort"
import type { Holding } from "@/lib/api/types"
import {
  formatCurrency,
  formatCurrencyWithDecimals,
  formatPercent,
  formatPercentOrDash,
  getPLColorClass,
} from "@/lib/format"
import { getLotStatusSortValue, getUnitLotGroups, hasUnitLot, isJapaneseStock } from "@/lib/holding-lot"

interface HoldingsTableProps {
  holdings: Holding[] | undefined
  isLoading: boolean
  weeklyChangeMap?: ReadonlyMap<string, number>
}

type SortKey =
  | "symbol"
  | "quantity"
  | "lot_status"
  | "current_price"
  | "market_value"
  | "total_pl"
  | "total_pl_percentage"
  | "weekly_change"

function UnitLotIndicator({ holding }: { holding: Holding }) {
  if (!isJapaneseStock(holding)) {
    return <span className="text-muted-foreground">-</span>
  }

  const hasUnit = hasUnitLot(holding)
  const unitLotGroups = getUnitLotGroups(holding)
  const accountBreakdown =
    unitLotGroups.length > 0
      ? unitLotGroups.map((group) => `${group.label}: ${group.quantity.toLocaleString()}株`).join(" / ")
      : "口座別数量なし"
  const label = hasUnit ? `単元あり。${accountBreakdown}` : `単元未満。${accountBreakdown}`

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span
          aria-label={label}
          role="img"
          className="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground"
        >
          {hasUnit ? (
            <CircleCheck className="h-5 w-5 text-emerald-600" aria-hidden="true" />
          ) : (
            <CircleMinus className="h-5 w-5 text-muted-foreground" aria-hidden="true" />
          )}
        </span>
      </TooltipTrigger>
      <TooltipContent side="top">
        <p>{label}</p>
      </TooltipContent>
    </Tooltip>
  )
}

export function HoldingsTable({ holdings, isLoading, weeklyChangeMap }: HoldingsTableProps) {
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
        case "lot_status":
          aValue = getLotStatusSortValue(a)
          bValue = getLotStatusSortValue(b)
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
        case "weekly_change":
          aValue = weeklyChangeMap?.get(a.symbol) ?? Number.NEGATIVE_INFINITY
          bValue = weeklyChangeMap?.get(b.symbol) ?? Number.NEGATIVE_INFINITY
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
                    className="w-16 cursor-pointer select-none text-center"
                    onClick={() => handleSort("lot_status")}
                  >
                    <div className="flex items-center justify-center">
                      単元
                      {getSortIcon("lot_status")}
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
                  <TableHead
                    className="cursor-pointer select-none text-right"
                    onClick={() => handleSort("weekly_change")}
                  >
                    <div className="flex items-center justify-end">
                      週次騰落率
                      {getSortIcon("weekly_change")}
                    </div>
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sortedHoldings && sortedHoldings.length > 0 ? (
                  sortedHoldings.map((holding) => {
                    const plValue = holding.total_pl ?? 0
                    const plColor = getPLColorClass(plValue)
                    const weeklyChange = weeklyChangeMap?.get(holding.symbol)
                    const weeklyChangeText = formatPercentOrDash(weeklyChange)
                    const weeklyChangeColor = weeklyChange !== undefined ? getPLColorClass(weeklyChange) : ""

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
                        <TableCell className="text-center">
                          <UnitLotIndicator holding={holding} />
                        </TableCell>
                        <TableCell className="text-right">
                          <div>
                            <div>
                              {holding.current_price ? formatCurrency(holding.current_price, "JPY") : "-"}
                            </div>
                            {holding.currency === "USD" ? (
                              <div className="text-xs text-muted-foreground">
                                {holding.current_price_usd
                                  ? formatCurrencyWithDecimals(holding.current_price_usd, "USD")
                                  : "-"}
                              </div>
                            ) : null}
                          </div>
                        </TableCell>
                        <TableCell className="text-right">
                          <div>
                            <div>
                              {holding.market_value ? formatCurrency(holding.market_value, "JPY") : "-"}
                            </div>
                            {holding.currency === "USD" ? (
                              <div className="text-xs text-muted-foreground">
                                {holding.market_value_usd
                                  ? formatCurrency(holding.market_value_usd, "USD")
                                  : "-"}
                              </div>
                            ) : null}
                          </div>
                        </TableCell>
                        <TableCell className={`text-right font-medium ${plColor}`}>
                          {holding.total_pl ? formatCurrency(holding.total_pl) : "-"}
                        </TableCell>
                        <TableCell className={`text-right font-medium ${plColor}`}>
                          {holding.total_pl_percentage ? formatPercent(holding.total_pl_percentage) : "-"}
                        </TableCell>
                        <TableCell className={`text-right font-medium ${weeklyChangeColor}`}>
                          {weeklyChangeText}
                        </TableCell>
                      </TableRow>
                    )
                  })
                ) : (
                  <TableRow>
                    <TableCell colSpan={8} className="text-center text-muted-foreground">
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
