import { useMemo, useState } from "react"
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
import type { PriceHistoryInterval, PriceHistoryPeriod, TransactionWithPL } from "@/lib/api/types"

interface PriceChartProps {
  symbol: string
  securityType?: string | null
  transactions?: TransactionWithPL[]
}

export function PriceChart({ symbol, securityType, transactions }: PriceChartProps) {
  const [period, setPeriod] = useState<PriceHistoryPeriod>("1Y")
  const [interval, setInterval] = useState<PriceHistoryInterval>("daily")

  const { data, isLoading, error } = useSWR(
    securityType === "FUND" ? null : `/stocks/${symbol}/price-history?period=${period}&interval=${interval}`,
    () => getPriceHistory(symbol, period, interval)
  )

  // 買付日を抽出し、グラフの日付範囲内のもののみをフィルタリング
  const buyDates = useMemo(() => {
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
  }, [transactions, data])

  // 年の変わり目を検出
  // 注意: 日付文字列はYYYY-MM-DD形式なので、直接文字列から年を抽出する
  // new Date()を使うとタイムゾーンの影響で年がずれる可能性があるため
  const yearBoundaries = useMemo(() => {
    if (!data?.data || data.data.length === 0) return []

    const boundaries: { date: string; year: number }[] = []
    let currentYear: number | null = null

    for (const item of data.data) {
      // YYYY-MM-DD形式の日付文字列から年を直接抽出
      const year = Number.parseInt(item.date.substring(0, 4), 10)

      if (currentYear !== null && year !== currentYear) {
        // 年が変わった最初のデータポイントを記録
        boundaries.push({ date: item.date, year })
      }
      currentYear = year
    }

    return boundaries
  }, [data])

  // 投資信託の場合は非表示
  if (securityType === "FUND") {
    return null
  }

  const periodButtons: { label: string; value: PriceHistoryPeriod }[] = [
    { label: "1M", value: "1M" },
    { label: "3M", value: "3M" },
    { label: "6M", value: "6M" },
    { label: "1Y", value: "1Y" },
    { label: "3Y", value: "3Y" },
  ]

  const intervalButtons: { label: string; value: PriceHistoryInterval }[] = [
    { label: "日足", value: "daily" },
    { label: "週足", value: "weekly" },
    { label: "月足", value: "monthly" },
  ]

  return (
    <Card>
      <CardHeader>
        <CardTitle>株価推移</CardTitle>
        <div className="flex flex-wrap items-center gap-2">
          {/* 期間選択 */}
          <div className="flex gap-1">
            {periodButtons.map((btn) => (
              <button
                key={btn.value}
                type="button"
                onClick={() => setPeriod(btn.value)}
                className={`rounded-md px-3 py-1 text-sm font-medium transition-colors ${
                  period === btn.value
                    ? "bg-primary text-primary-foreground"
                    : "bg-secondary text-secondary-foreground hover:bg-secondary/80"
                }`}
              >
                {btn.label}
              </button>
            ))}
          </div>

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
              <XAxis
                dataKey="date"
                tickFormatter={(value) => {
                  const date = new Date(value)
                  return `${date.getMonth() + 1}/${date.getDate()}`
                }}
              />
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
              {/* 年の変わり目の参照線 */}
              {yearBoundaries.map(({ date, year }) => (
                <ReferenceLine
                  key={`year-${date}`}
                  x={date}
                  stroke="hsl(var(--muted-foreground))"
                  strokeDasharray="5 5"
                  label={{
                    value: year.toString(),
                    position: "top",
                    fill: "hsl(var(--muted-foreground))",
                    fontSize: 12,
                  }}
                />
              ))}
              {/* 買付日の参照線 */}
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
