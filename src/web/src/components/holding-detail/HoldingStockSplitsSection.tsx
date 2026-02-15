import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import type { StockSplit } from "@/lib/api/types"
import { formatDate } from "@/lib/format"

interface HoldingStockSplitsSectionProps {
  stockSplits: StockSplit[] | undefined
  isLoading: boolean
}

export function HoldingStockSplitsSection({ stockSplits, isLoading }: HoldingStockSplitsSectionProps) {
  const formatSplitRatio = (ratio: number) => {
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
            {[...Array(3)].map((_, i) => (
              // biome-ignore lint/suspicious/noArrayIndexKey: Static skeleton loading elements
              <div key={`skeleton-${i}`} className="h-12 animate-pulse rounded bg-muted" />
            ))}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>分割日</TableHead>
                  <TableHead className="text-right">分割比率</TableHead>
                  <TableHead className="text-right">登録日</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {stockSplits && stockSplits.length > 0 ? (
                  stockSplits.map((stockSplit) => (
                    <TableRow key={stockSplit.split_id}>
                      <TableCell>{formatDate(stockSplit.split_date)}</TableCell>
                      <TableCell className="text-right font-medium">
                        {formatSplitRatio(stockSplit.split_ratio)}
                      </TableCell>
                      <TableCell className="text-right text-sm text-muted-foreground">
                        {formatDate(stockSplit.created_at)}
                      </TableCell>
                    </TableRow>
                  ))
                ) : (
                  <TableRow>
                    <TableCell colSpan={3} className="text-center text-muted-foreground">
                      株式分割履歴がありません
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
