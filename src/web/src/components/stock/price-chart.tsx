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
import type { PriceDataPoint, PriceHistoryInterval, TransactionWithPL } from "@/lib/api/types"

interface PriceChartProps {
  symbol: string
  securityType?: string | null
  transactions?: TransactionWithPL[]
}

type TickFormat = "yyyy/mm" | "mm"

/**
 * 指定されたインターバルに基づいて、X軸に表示するティックと、各ティックのフォーマット形式を計算する
 * @param dataPoints - 株価データポイントの配列
 * @param interval - 表示間隔（daily, weekly, monthly）
 * @returns ティックの日付文字列配列と、各日付のフォーマット形式を持つMap
 */
function calculateTicksForInterval(
  dataPoints: PriceDataPoint[],
  interval: PriceHistoryInterval
): { ticks: string[]; formatMap: Map<string, TickFormat> } {
  const ticks: string[] = []
  const formatMap = new Map<string, TickFormat>()

  if (dataPoints.length === 0) {
    return { ticks, formatMap }
  }

  const quarterMonths = [1, 4, 7, 10]
  let prevYear: number | null = null
  let prevMonth: number | null = null

  for (const point of dataPoints) {
    const date = new Date(point.date)
    const year = date.getFullYear()
    const month = date.getMonth() + 1

    const isFirst = prevMonth === null
    const hasMonthChanged = prevMonth !== null && month !== prevMonth
    const isYearChange = prevYear !== null && year !== prevYear

    let shouldAddTick = false

    if (interval === "daily") {
      // 日足: 月が変わった最初のデータ
      shouldAddTick = isFirst || hasMonthChanged
    } else if (interval === "weekly") {
      // 週足: 最初 or 四半期開始月の最初のデータ
      shouldAddTick = isFirst || (hasMonthChanged && quarterMonths.includes(month))
    } else {
      // 月足: 1月のみ
      shouldAddTick = month === 1
    }

    if (shouldAddTick) {
      ticks.push(point.date)

      // 月足は常にyyyy/mm、他は最初or年変わりでyyyy/mm
      if (interval === "monthly") {
        formatMap.set(point.date, "yyyy/mm")
      } else {
        formatMap.set(point.date, isFirst || isYearChange ? "yyyy/mm" : "mm")
      }
    }

    prevYear = year
    prevMonth = month
  }

  return { ticks, formatMap }
}

export function PriceChart({ symbol, securityType, transactions }: PriceChartProps) {
  const [interval, setInterval] = useState<PriceHistoryInterval>("daily")
  const limit = interval === "monthly" ? 60 : 80

  const { data, isLoading, error } = useSWR(
    securityType === "FUND" ? null : `/stocks/${symbol}/price-history?interval=${interval}&limit=${limit}`,
    () => getPriceHistory(symbol, interval, limit)
  )

  const chartData = useMemo(() => {
    if (!data?.data) return []
    return data.data.map((point) => ({
      ...point,
      dateMs: new Date(point.date).getTime(),
    }))
  }, [data?.data])

  // ティックの計算
  const ticksConfig = useMemo(() => {
    if (!data?.data) {
      return { ticks: [], formatMap: new Map<string, TickFormat>() }
    }
    return calculateTicksForInterval(data.data, interval)
  }, [data?.data, interval])

  const ticksMs = useMemo(() => ticksConfig.ticks.map((date) => new Date(date).getTime()), [ticksConfig])
  const tickFormatMapMs = useMemo(() => {
    const map = new Map<number, TickFormat>()
    for (const date of ticksConfig.ticks) {
      const format = ticksConfig.formatMap.get(date)
      if (format) {
        map.set(new Date(date).getTime(), format)
      }
    }
    return map
  }, [ticksConfig])

  // 投資信託の場合は非表示
  if (securityType === "FUND") {
    return null
  }

  const intervalButtons: { label: string; value: PriceHistoryInterval }[] = [
    { label: "日足", value: "daily" },
    { label: "週足", value: "weekly" },
    { label: "月足", value: "monthly" },
  ]

  // 買付日を抽出し、グラフの日付範囲内のもののみをフィルタリング
  const buyDatesMs = (() => {
    if (!transactions || chartData.length === 0) return []

    const chartDateMsList = chartData.map((point) => point.dateMs)
    const minDateMs = Math.min(...chartDateMsList)
    const maxDateMs = Math.max(...chartDateMsList)

    return transactions
      .filter((t) => t.transaction_type === "buy")
      .map((t) => t.transaction_date.split("T")[0])
      .map((date) => new Date(date).getTime())
      .filter((dateMs) => dateMs >= minDateMs && dateMs <= maxDateMs)
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
        ) : chartData.length > 0 ? (
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="dateMs"
                type="number"
                domain={["dataMin", "dataMax"]}
                ticks={ticksMs}
                interval={0}
                tickFormatter={(value: number) => {
                  const format = tickFormatMapMs.get(value)
                  if (!format) return ""

                  const date = new Date(value)
                  const year = date.getFullYear()
                  const month = date.getMonth() + 1
                  const monthStr = month.toString().padStart(2, "0")

                  return format === "yyyy/mm" ? `${year}/${monthStr}` : monthStr
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
                  if (typeof value !== "number") return ""
                  const date = new Date(value)
                  return `${date.getFullYear()}/${date.getMonth() + 1}/${date.getDate()}`
                }}
                formatter={(value) => [typeof value === "number" ? value.toLocaleString() : "0", "終値"]}
              />
              <Line type="monotone" dataKey="close" stroke="var(--primary)" strokeWidth={2} dot={false} />
              {buyDatesMs.map((dateMs) => (
                <ReferenceLine key={dateMs} x={dateMs} stroke="red" />
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
