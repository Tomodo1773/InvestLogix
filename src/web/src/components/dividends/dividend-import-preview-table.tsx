import { Check } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import type { CsvDividendPreview } from "@/lib/api/types"
import { formatDate } from "@/lib/format"

interface DividendImportPreviewTableProps {
  dividends: CsvDividendPreview[]
  onConfirm: () => void
  isLoading: boolean
}

export function DividendImportPreviewTable({
  dividends,
  onConfirm,
  isLoading,
}: DividendImportPreviewTableProps) {
  const formatNumber = (num: number | null) => {
    if (num === null) return "-"
    return num.toLocaleString("ja-JP")
  }

  return (
    <div className="space-y-4">
      <div className="overflow-x-auto rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>受渡日</TableHead>
              <TableHead>シンボル</TableHead>
              <TableHead>銘柄名</TableHead>
              <TableHead className="text-right">数量</TableHead>
              <TableHead className="text-right">受取額</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {dividends.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-muted-foreground">
                  新規登録する配当金はありません
                </TableCell>
              </TableRow>
            ) : (
              dividends.map((div, index) => (
                <TableRow key={`${div.symbol}-${div.payment_date}-${index}`}>
                  <TableCell>{formatDate(div.payment_date)}</TableCell>
                  <TableCell className="font-mono">{div.symbol}</TableCell>
                  <TableCell>{div.name}</TableCell>
                  <TableCell className="text-right">{formatNumber(div.shares_owned)}</TableCell>
                  <TableCell className="text-right">¥{formatNumber(div.total_amount)}</TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {dividends.length > 0 && (
        <Button onClick={onConfirm} disabled={isLoading} className="w-full">
          {isLoading ? (
            <>
              <Check className="mr-2 h-4 w-4 animate-spin" />
              登録中...
            </>
          ) : (
            <>
              <Check className="mr-2 h-4 w-4" />
              {dividends.length}件の配当金を登録
            </>
          )}
        </Button>
      )}
    </div>
  )
}
