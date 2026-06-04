import type { WeeklyPerformanceResponse } from "@/lib/api/types"

export function buildWeeklyChangeMap(
  weeklyPerformance: WeeklyPerformanceResponse | undefined
): ReadonlyMap<string, number> | undefined {
  if (!weeklyPerformance?.all_performers) return undefined
  return new Map(
    weeklyPerformance.all_performers.map((performer) => [performer.symbol, performer.change_rate])
  )
}
