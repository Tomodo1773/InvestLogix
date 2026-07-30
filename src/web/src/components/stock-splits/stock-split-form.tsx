import type * as React from "react"
import { useState } from "react"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { createStockSplit } from "@/lib/api/client"
import { formatSplitRatio, splitRatioFromShares } from "@/lib/stock-split"

interface StockSplitFormProps {
  /** 登録に成功したとき（呼び出し側で一覧を再取得してフォームを閉じる） */
  onCreated: () => void
  onCancel: () => void
}

const SYMBOL_MAX_LENGTH = 15

/** 入力中の株数から、登録内容のプレビューまたは入力の不備を伝える文言を組み立てる */
function buildRatioHint(ratio: number | null): string {
  if (ratio === null) {
    return "分割前・分割後の株数には 1 以上の数を入力してください"
  }
  if (ratio === 1) {
    return "分割前と分割後で異なる株数を入力してください"
  }
  return `登録内容: ${formatSplitRatio(ratio)}`
}

export function StockSplitForm({ onCreated, onCancel }: StockSplitFormProps) {
  const [symbol, setSymbol] = useState("")
  const [splitDate, setSplitDate] = useState("")
  const [sharesBefore, setSharesBefore] = useState("1")
  const [sharesAfter, setSharesAfter] = useState("2")
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const ratio = splitRatioFromShares(Number(sharesBefore), Number(sharesAfter))
  const canSubmit = symbol.trim() !== "" && splitDate !== "" && ratio !== null && ratio !== 1

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!canSubmit || ratio === null) {
      return
    }

    setIsSubmitting(true)
    setError(null)
    try {
      await createStockSplit({
        symbol: symbol.trim(),
        split_date: splitDate,
        split_ratio: ratio,
      })
      onCreated()
    } catch (e) {
      setError(e instanceof Error ? e.message : "株式分割の登録に失敗しました")
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>株式分割を登録</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="split-symbol">銘柄コード</Label>
              <Input
                id="split-symbol"
                value={symbol}
                onChange={(e) => setSymbol(e.target.value)}
                maxLength={SYMBOL_MAX_LENGTH}
                placeholder="7203 / AAPL"
                disabled={isSubmitting}
              />
              <p className="text-sm text-muted-foreground">取引実績のある銘柄コードを入力してください</p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="split-date">分割基準日</Label>
              <Input
                id="split-date"
                type="date"
                value={splitDate}
                onChange={(e) => setSplitDate(e.target.value)}
                disabled={isSubmitting}
              />
              <p className="text-sm text-muted-foreground">この日より前の取引が調整対象になります</p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="split-shares-before">分割前株数</Label>
              <Input
                id="split-shares-before"
                type="number"
                min="1"
                step="1"
                value={sharesBefore}
                onChange={(e) => setSharesBefore(e.target.value)}
                disabled={isSubmitting}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="split-shares-after">分割後株数</Label>
              <Input
                id="split-shares-after"
                type="number"
                min="1"
                step="1"
                value={sharesAfter}
                onChange={(e) => setSharesAfter(e.target.value)}
                disabled={isSubmitting}
              />
            </div>
          </div>

          <p className="text-sm text-muted-foreground">{buildRatioHint(ratio)}</p>

          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <div className="flex justify-end gap-2">
            <Button type="button" variant="ghost" onClick={onCancel} disabled={isSubmitting}>
              キャンセル
            </Button>
            <Button type="submit" disabled={!canSubmit || isSubmitting}>
              {isSubmitting ? "登録中..." : "登録"}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}
