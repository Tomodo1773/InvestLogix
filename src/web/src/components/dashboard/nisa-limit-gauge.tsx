import { useMemo } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import type { MonthlySummaryItem } from "@/lib/api/types"

interface NisaLimitGaugeProps {
  data: MonthlySummaryItem[] | undefined
  isLoading: boolean
}

const NISA_LIMITS = {
  NISAGrowth: 2_400_000, // 成長投資枠: 240万円
  NISAAccumulation: 1_200_000, // つみたて投資枠: 120万円
}

const ACCOUNT_LABELS = {
  NISAGrowth: "成長投資枠",
  NISAAccumulation: "つみたて投資枠",
}

export function NisaLimitGauge({ data, isLoading }: NisaLimitGaugeProps) {
  const yearlyTotals = useMemo(() => {
    if (!data || data.length === 0) {
      return {
        NISAGrowth: 0,
        NISAAccumulation: 0,
      }
    }

    const currentYear = new Date().getFullYear()
    const currentYearData = data.filter((item) => item.year === currentYear)

    const totals = {
      NISAGrowth: 0,
      NISAAccumulation: 0,
    }

    for (const item of currentYearData) {
      if (item.total_purchase.NISAGrowth) {
        totals.NISAGrowth += item.total_purchase.NISAGrowth
      }
      if (item.total_purchase.NISAAccumulation) {
        totals.NISAAccumulation += item.total_purchase.NISAAccumulation
      }
    }

    return totals
  }, [data])

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>NISA投資枠</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-32 animate-pulse rounded bg-muted" />
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>NISA投資枠</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        <Progress
          value={yearlyTotals.NISAGrowth}
          max={NISA_LIMITS.NISAGrowth}
          label={ACCOUNT_LABELS.NISAGrowth}
          colorClass="bg-green-600"
        />
        <Progress
          value={yearlyTotals.NISAAccumulation}
          max={NISA_LIMITS.NISAAccumulation}
          label={ACCOUNT_LABELS.NISAAccumulation}
          colorClass="bg-teal-600"
        />
      </CardContent>
    </Card>
  )
}
