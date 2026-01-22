import { ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react"
import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import type { Transaction } from "@/lib/api/types"
import { formatCurrency } from "@/lib/format"

interface TransactionsTableProps {
  transactions: Transaction[] | undefined
  isLoading: boolean
}

type SortKey = "symbol" | "transaction_date" | "quantity" | "price" | "total_amount"
type SortDirection = "asc" | "desc"

export function TransactionsTable({ transactions, isLoading }: TransactionsTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>("transaction_date")
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc")

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDirection(sortDirection === "asc" ? "desc" : "asc")
    } else {
      setSortKey(key)
      setSortDirection("desc")
    }
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

  const sortedTransactions = transactions?.sort((a, b) => {
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
        aValue = Number(a.quantity)
        bValue = Number(b.quantity)
        break
      case "price":
        aValue = Number(a.price)
        bValue = Number(b.price)
        break
      case "total_amount":
        aValue = Number(a.quantity) * Number(a.price)
        bValue = Number(b.quantity) * Number(b.price)
        break
    }

    if (typeof aValue === "string" && typeof bValue === "string") {
      return sortDirection === "asc" ? aValue.localeCompare(bValue) : bValue.localeCompare(aValue)
    }

    return sortDirection === "asc"
      ? (aValue as number) - (bValue as number)
      : (bValue as number) - (aValue as number)
  })

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleDateString("ja-JP", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    })
  }

  const getAccountTypeLabel = (accountType: string) => {
    return accountType === "nisa" ? "NISA" : "特定"
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>取引履歴</CardTitle>
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
                  <TableHead
                    className="cursor-pointer select-none text-right"
                    onClick={() => handleSort("transaction_date")}
                  >
                    <div className="flex items-center justify-end">
                      日付
                      {getSortIcon("transaction_date")}
                    </div>
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sortedTransactions && sortedTransactions.length > 0 ? (
                  sortedTransactions.map((transaction) => {
                    const totalAmount = Number(transaction.quantity) * Number(transaction.price)
                    const isBuy = transaction.transaction_type === "buy"

                    return (
                      <TableRow key={transaction.transaction_id}>
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
                        <TableCell className="text-right">
                          {Number(transaction.quantity).toLocaleString()}
                        </TableCell>
                        <TableCell className="text-right">{formatCurrency(transaction.price)}</TableCell>
                        <TableCell className="text-right">{formatCurrency(totalAmount.toString())}</TableCell>
                        <TableCell className="text-right">
                          {formatDate(transaction.transaction_date)}
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
