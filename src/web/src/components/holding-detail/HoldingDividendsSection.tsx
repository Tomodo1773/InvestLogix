import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import type { Dividend } from "@/lib/api/types"
import { formatCurrency, formatDate } from "@/lib/format"

interface HoldingDividendsSectionProps {
  dividends: Dividend[] | undefined
  isLoading: boolean
}

export function HoldingDividendsSection({ dividends, isLoading }: HoldingDividendsSectionProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>配当金履歴</CardTitle>
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
                  <TableHead>支払日</TableHead>
                  <TableHead className="text-right">保有株数</TableHead>
                  <TableHead className="text-right">配当金額</TableHead>
                  <TableHead className="text-right">税金</TableHead>
                  <TableHead className="text-right">手数料</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {dividends && dividends.length > 0 ? (
                  dividends.map((dividend) => (
                    <TableRow key={dividend.dividend_id}>
                      <TableCell>{formatDate(dividend.payment_date)}</TableCell>
                      <TableCell className="text-right">{dividend.shares_owned.toLocaleString()}株</TableCell>
                      <TableCell className="text-right">{formatCurrency(dividend.total_amount)}</TableCell>
                      <TableCell className="text-right">
                        {dividend.tax ? formatCurrency(dividend.tax) : "-"}
                      </TableCell>
                      <TableCell className="text-right">
                        {dividend.fee ? formatCurrency(dividend.fee) : "-"}
                      </TableCell>
                    </TableRow>
                  ))
                ) : (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center text-muted-foreground">
                      配当金履歴がありません
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
