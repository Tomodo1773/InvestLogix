import { useState } from "react"
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import useSWR from "swr"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { getPriceHistory } from "@/lib/api/client"
import type { PriceHistoryInterval, TransactionWithPL } from "@/lib/api/types"

interface PriceChartProps {
  symbol: string
  securityType?: string | null
  transactions?: TransactionWithPL[]
}

export function PriceChart({ symbol, securityType, transactions }: PriceChartProps) {
  const [interval, setInterval] = useState<PriceHistoryInterval>("daily")

  const { data, isLoading, error } = useSWR(
    securityType === "FUND" ? null : `/stocks/${symbol}/price-history?interval=${interval}&limit=80`,
    () => getPriceHistory(symbol, interval, 80)
  )

  // 投資信託の場合は非表示
  if (securityType === "FUND") {
    return null
  }

  const intervalButtons: { label: string; value: PriceHistoryInterval }[] = [
    { label: "日足", value: "daily" },
    { label: "週足", value: "weekly" },
    { label: "月足", value: "monthly" },
  ]

  // X軸のフォーマット関数（間隔ごとに異なる形式）
  const formatXAxis = (value: string, index: number) => {
    if (!data?.data) return ""
    const date = new Date(value)
    const year = date.getFullYear()
    const month = date.getMonth() + 1

    // 最初のデータポイントの年
    const firstDate = new Date(data.data[0].date)
    const firstYear = firstDate.getFullYear()

    if (interval === "daily") {
      // 日足: mm形式、月初のみ表示。最初と年が変わった時はyyyy/mm
      const isFirstOfMonth = date.getDate() === 1 || index === 0
      if (!isFirstOfMonth) return ""

      const isFirstPoint = index === 0
      const isYearChange = year !== firstYear && month === 1

      if (isFirstPoint || isYearChange) {
        return `${year}/${month.toString().padStart(2, "0")}`
      }
      return month.toString().padStart(2, "0")
    }

    if (interval === "weekly") {
      // 週足: mm形式、3ヶ月毎（1,4,7,10月）。最初と年が変わった時はyyyy/mm
      const isQuarterStart = [1, 4, 7, 10].includes(month)
      if (!isQuarterStart && index !== 0) return ""

      const isFirstPoint = index === 0
      const isYearChange = year !== firstYear && month === 1

      if (isFirstPoint || isYearChange) {
        return `${year}/${month.toString().padStart(2, "0")}`
      }
      return month.toString().padStart(2, "0")
    }

    // 月足: yyyy/mm形式、1月のみ表示
    if (month !== 1) return ""
    return `${year}/${month.toString().padStart(2, "0")}`
  }

  // 買付日を抽出し、グラフの日付範囲内のもののみをフィルタリング
  const buyDates = (() => {
    if (!transactions || !data?.data || data.data.length === 0) return []

    // 株価データの日付はYYYY-MM-DD形式
    const chartDates = new Set(data.data.map((d) => d.date))

    // トランザクションの日付はISO形式（例: 2024-01-15T00:00:00+09:00）なので
    // YYYY-MM-DD部分のみを抽出して比較する
    const buyTransactionDates = transactions
      .filter((t) => t.transaction_type === "buy")
      .map((t) => t.transaction_date.split("T")[0])

    // グラフの日付範囲内にある買付日のみを返す
    return buyTransactionDates.filter((date) => chartDates.has(date))
  })()

  return (
    <Card>
      <CardHeader>
        <CardTitle>株価推移</CardTitle>
        <div className="flex flex-wrap items-center gap-2">
          {/* 間隔選択 */}
          <div className="flex gap-1">
            {intervalButtons.map((btn) => (
              <button
                key={btn.value}
                type="button"
                onClick={() => setInterval(btn.value)}
                className={`rounded-md px-3 py-1 text-sm font-medium transition-colors ${
                  interval === btn.value
                    ? "bg-primary text-primary-foreground"
                    : "bg-secondary text-secondary-foreground hover:bg-secondary/80"
                }`}
              >
                {btn.label}
              </button>
            ))}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex h-[400px] items-center justify-center">
            <div className="h-12 w-12 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          </div>
        ) : error ? (
          <div className="flex h-[400px] items-center justify-center">
            <p className="text-muted-foreground">データを取得できませんでした</p>
          </div>
        ) : data?.data && data.data.length > 0 ? (
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={data.data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" tickFormatter={formatXAxis} />
              <YAxis domain={["auto", "auto"]} tickFormatter={(value) => value.toLocaleString()} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "hsl(var(--background))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: "var(--radius)",
                }}
                labelFormatter={(value) => {
                  const date = new Date(value)
                  return `${date.getFullYear()}/${date.getMonth() + 1}/${date.getDate()}`
                }}
                formatter={(value: number | undefined) => [value?.toLocaleString() ?? "0", "終値"]}
              />
              <Line type="monotone" dataKey="close" stroke="var(--primary)" strokeWidth={2} dot={false} />
              {buyDates.map((date) => (
                <ReferenceLine key={date} x={date} stroke="red" />
              ))}
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex h-[400px] items-center justify-center">
            <p className="text-muted-foreground">データがありません</p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
