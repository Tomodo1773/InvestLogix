interface ProgressProps {
  value: number
  max: number
  label: string
  colorClass?: string
}

export function Progress({ value, max, label, colorClass = "bg-green-500" }: ProgressProps) {
  const percentage = max > 0 ? Math.min((value / max) * 100, 100) : 0
  const isOverLimit = value > max

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium">{label}</span>
        <span className={`text-sm ${isOverLimit ? "text-red-600" : "text-muted-foreground"}`}>
          {percentage.toFixed(1)}%
        </span>
      </div>
      <div className="h-3 w-full overflow-hidden rounded-full bg-gray-200">
        <div
          className={`h-full transition-all ${isOverLimit ? "bg-red-500" : colorClass}`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>
          ¥{value.toLocaleString()} / ¥{max.toLocaleString()}
        </span>
        <span className={isOverLimit ? "text-red-600" : ""}>
          残り ¥{Math.max(max - value, 0).toLocaleString()}
        </span>
      </div>
    </div>
  )
}
