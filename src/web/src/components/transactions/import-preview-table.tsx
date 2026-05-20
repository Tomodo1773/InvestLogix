import { Check } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import type { CsvTransactionPreview } from "@/lib/api/types"
import { formatDate } from "@/lib/format"

interface ImportPreviewTableProps {
  transactions: CsvTransactionPreview[]
  onConfirm: () => void
  isLoading: boolean
}

export function ImportPreviewTable({ transactions, onConfirm, isLoading }: ImportPreviewTableProps) {
  const formatNumber = (num: number | null) => {
    if (num === null) return "-"
    return num.toLocaleString("ja-JP")
  }

  const formatTransactionType = (type: "buy" | "sell") => {
    return type === "buy" ? "買付" : "売却"
  }

  return (
    <div className="space-y-4">
      <div className="overflow-x-auto rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>約定日</TableHead>
              <TableHead>シンボル</TableHead>
              <TableHead>銘柄名</TableHead>
              <TableHead>取引種別</TableHead>
              <TableHead className="text-right">数量</TableHead>
              <TableHead className="text-right">単価</TableHead>
              <TableHead>口座種別</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {transactions.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center text-muted-foreground">
                  新規登録する取引はありません
                </TableCell>
              </TableRow>
            ) : (
              transactions.map((tx) => (
                <TableRow
                  key={`${tx.symbol}-${tx.transaction_date}-${tx.transaction_type}-${tx.quantity}-${tx.price}-${tx.account_type}`}
                >
                  <TableCell>{formatDate(tx.transaction_date)}</TableCell>
                  <TableCell className="font-mono">{tx.symbol}</TableCell>
                  <TableCell>{tx.name}</TableCell>
                  <TableCell>{formatTransactionType(tx.transaction_type)}</TableCell>
                  <TableCell className="text-right">{formatNumber(tx.quantity)}</TableCell>
                  <TableCell className="text-right">¥{formatNumber(tx.price)}</TableCell>
                  <TableCell>{tx.account_type}</TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {transactions.length > 0 && (
        <Button onClick={onConfirm} disabled={isLoading} className="w-full">
          {isLoading ? (
            <>
              <Check className="mr-2 h-4 w-4 animate-spin" />
              登録中...
            </>
          ) : (
            <>
              <Check className="mr-2 h-4 w-4" />
              {transactions.length}件の取引を登録
            </>
          )}
        </Button>
      )}
    </div>
  )
}
