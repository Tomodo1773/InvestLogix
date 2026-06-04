import { useMemo, useState } from "react"
import { useNavigate } from "react-router"
import { ResponsiveContainer, Tooltip, Treemap } from "recharts"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { Holding } from "@/lib/api/types"
import { type ColorScale, computeColorScale, getColorForValue } from "@/lib/color-scale"
import { formatCurrency, formatPercent, formatPercentOrDash } from "@/lib/format"

type Country = "JP" | "US" | "OTHER"
type CountryFilter = "ALL" | Country
type ColorMetric = "weekly_change" | "unrealized_pl_percentage"

interface SectorTreemapProps {
  data: Holding[] | undefined
  isLoading: boolean
  weeklyChangeMap?: ReadonlyMap<string, number>
}

interface TreemapLeaf {
  name: string
  value: number
  symbol: string
  stockName: string
  country: Country
  sectorName: string
  colorValue: number | null
  weeklyChangeRate: number | null
  plPercentage: number | null
}

interface TreemapSector {
  name: string
  children: TreemapLeaf[]
  value: number
}

interface TreemapCountry {
  name: string
  children: TreemapSector[]
  value: number
}

const COUNTRY_LABELS: Record<Country, string> = {
  JP: "日本",
  US: "米国",
  OTHER: "その他",
}

const COUNTRY_FILTERS: { value: CountryFilter; label: string }[] = [
  { value: "ALL", label: "すべて" },
  { value: "JP", label: COUNTRY_LABELS.JP },
  { value: "US", label: COUNTRY_LABELS.US },
  { value: "OTHER", label: COUNTRY_LABELS.OTHER },
]

const COLOR_METRIC_LABELS: Record<ColorMetric, string> = {
  weekly_change: "1週間騰落率",
  unrealized_pl_percentage: "損益率",
}

const COLOR_METRIC_OPTIONS: { value: ColorMetric; label: string }[] = [
  { value: "weekly_change", label: COLOR_METRIC_LABELS.weekly_change },
  { value: "unrealized_pl_percentage", label: COLOR_METRIC_LABELS.unrealized_pl_percentage },
]

function normalizeCountry(c: Holding["country"]): Country {
  if (c === "JP" || c === "US") return c
  return "OTHER"
}

/**
 * 保有銘柄を国 → セクター → 銘柄の3階層ツリーマップ用データに変換する。
 * 評価額（market_value）が 0 以下の銘柄、フィルタ条件に合わない銘柄は除外。
 * country が null や未知の値、sector_name が null のものは "OTHER"/"その他" に集約する。
 */
export function transformHoldingsToTreemap(
  holdings: Holding[] | undefined,
  filters: {
    country: CountryFilter
    colorMetric: ColorMetric
    weeklyChangeMap?: ReadonlyMap<string, number>
  }
): TreemapCountry[] {
  if (!holdings || holdings.length === 0) return []

  const byCountry = new Map<Country, Map<string, TreemapLeaf[]>>()
  for (const h of holdings) {
    if ((h.market_value ?? 0) <= 0) continue
    if (h.security_type !== "STOCK") continue
    const country = normalizeCountry(h.country)
    if (filters.country !== "ALL" && country !== filters.country) continue

    const sectorKey = h.sector_name ?? "その他"
    const weeklyChangeRate = filters.weeklyChangeMap?.get(h.symbol) ?? null
    const plPercentage = h.unrealized_pl_percentage
    const colorValue = filters.colorMetric === "weekly_change" ? weeklyChangeRate : plPercentage

    let sectors = byCountry.get(country)
    if (!sectors) {
      sectors = new Map()
      byCountry.set(country, sectors)
    }
    let leaves = sectors.get(sectorKey)
    if (!leaves) {
      leaves = []
      sectors.set(sectorKey, leaves)
    }
    leaves.push({
      name: h.stock_name || h.symbol,
      value: h.market_value ?? 0,
      symbol: h.symbol,
      stockName: h.stock_name || h.symbol,
      country,
      sectorName: sectorKey,
      colorValue,
      weeklyChangeRate,
      plPercentage,
    })
  }

  const result: TreemapCountry[] = []
  for (const [country, sectors] of byCountry.entries()) {
    const sectorBranches: TreemapSector[] = []
    let countryTotal = 0
    for (const [sectorName, leaves] of sectors.entries()) {
      leaves.sort((a, b) => b.value - a.value)
      const sectorTotal = leaves.reduce((s, l) => s + l.value, 0)
      sectorBranches.push({ name: sectorName, children: leaves, value: sectorTotal })
      countryTotal += sectorTotal
    }
    sectorBranches.sort((a, b) => b.value - a.value)
    result.push({ name: COUNTRY_LABELS[country], children: sectorBranches, value: countryTotal })
  }
  result.sort((a, b) => b.value - a.value)
  return result
}

/** カラースケール計算用に leaf の色指標値を平らな配列で取り出す */
export function flattenColorValues(data: TreemapCountry[]): Array<number | null> {
  const out: Array<number | null> = []
  for (const country of data) {
    for (const sector of country.children) {
      for (const leaf of sector.children) {
        out.push(leaf.colorValue)
      }
    }
  }
  return out
}

interface CellRenderProps {
  x?: number
  y?: number
  width?: number
  height?: number
  depth?: number
  name?: string
  colorValue?: number | null
  weeklyChangeRate?: number | null
  plPercentage?: number | null
  symbol?: string
  stockName?: string
  children?: CellRenderProps[] | null
  tooltipIndex?: string
}

function canRenderGroupLabel(width: number, height: number): boolean {
  return width >= 96 && height >= 28
}

const SECTOR_PADDING = 5
const SECTOR_HEADER_HEIGHT = 20
const LEAF_LABEL_FONT_SIZE = 9.5

type CellRect = Required<Pick<CellRenderProps, "x" | "y" | "width" | "height">>

function getLeafKey(props: CellRenderProps): string | null {
  return props.tooltipIndex ?? props.symbol ?? null
}

function scaleLeafIntoSector(child: CellRenderProps, sector: CellRect): CellRenderProps {
  const childX = child.x ?? 0
  const childY = child.y ?? 0
  const innerX = sector.x + SECTOR_PADDING
  const innerY = sector.y + SECTOR_HEADER_HEIGHT
  const innerWidth = Math.max(sector.width - SECTOR_PADDING * 2, 0)
  const innerHeight = Math.max(sector.height - SECTOR_HEADER_HEIGHT - SECTOR_PADDING, 0)

  return {
    ...child,
    x: innerX + ((childX - sector.x) / Math.max(sector.width, 1)) * innerWidth,
    y: innerY + ((childY - sector.y) / Math.max(sector.height, 1)) * innerHeight,
    width: ((child.width ?? 0) / Math.max(sector.width, 1)) * innerWidth,
    height: ((child.height ?? 0) / Math.max(sector.height, 1)) * innerHeight,
  }
}

function truncateLabel(label: string, maxLength: number): string {
  if (label.length <= maxLength) return label
  return `${label.slice(0, Math.max(maxLength - 1, 1))}...`
}

function renderLeafVisual(props: CellRenderProps, scale: ColorScale) {
  const { x = 0, y = 0, width = 0, height = 0, name } = props
  const showLabel = width >= 34 && height >= 18
  const label = truncateLabel(name || "", Math.floor((width - 8) / LEAF_LABEL_FONT_SIZE))

  return (
    <g key={`${x}-${y}-${name ?? ""}`}>
      <rect
        x={x}
        y={y}
        width={width}
        height={height}
        rx={2}
        ry={2}
        fill={getColorForValue(props.colorValue ?? null, scale)}
        stroke="#ffffff"
        strokeWidth={1}
      />
      {showLabel && (
        <text
          x={x + 4}
          y={y + 13}
          fill="#0f172a"
          fontSize={LEAF_LABEL_FONT_SIZE}
          fontWeight={700}
          pointerEvents="none"
        >
          {label}
        </text>
      )}
    </g>
  )
}

function renderTreemapCell(
  props: CellRenderProps,
  scale: ColorScale,
  leafLayout: Map<string, CellRect>,
  onLeafClick: (symbol: string) => void
) {
  const { x = 0, y = 0, width = 0, height = 0, depth = 0, name, symbol, children } = props
  const isLeaf = depth >= 3 && !!symbol
  const isSectorGroup = depth === 2 && !!children?.length

  if (isSectorGroup) {
    const sector = { x, y, width, height }
    const scaledChildren = children.map((child) => scaleLeafIntoSector(child, sector))
    for (const child of scaledChildren) {
      const key = getLeafKey(child)
      if (key) {
        leafLayout.set(key, {
          x: child.x ?? 0,
          y: child.y ?? 0,
          width: child.width ?? 0,
          height: child.height ?? 0,
        })
      }
    }

    return (
      <g>
        <rect x={x} y={y} width={width} height={height} rx={3} ry={3} fill="#f8fafc" stroke="none" />
        {scaledChildren.map((child) => renderLeafVisual(child, scale))}
        <rect
          x={x}
          y={y}
          width={width}
          height={height}
          rx={3}
          ry={3}
          fill="transparent"
          stroke="#e2e8f0"
          strokeWidth={1.5}
        />
        {canRenderGroupLabel(width, height) && (
          <text x={x + 6} y={y + 14} fill="#475569" fontSize={9.5} fontWeight={700} pointerEvents="none">
            {name}
          </text>
        )}
      </g>
    )
  }

  if (!isLeaf) {
    return (
      <rect x={x} y={y} width={width} height={height} fill="transparent" stroke="#cbd5e1" strokeWidth={1} />
    )
  }

  const leafKey = getLeafKey(props)
  const leafRect = leafKey ? leafLayout.get(leafKey) : undefined

  return (
    <g
      role="button"
      aria-label={name}
      tabIndex={0}
      style={{ cursor: "pointer" }}
      onClick={() => onLeafClick(symbol)}
      onKeyDown={(e: React.KeyboardEvent<SVGGElement>) => {
        if (e.key === "Enter" || e.key === " ") onLeafClick(symbol)
      }}
    >
      <rect
        x={leafRect?.x ?? x}
        y={leafRect?.y ?? y}
        width={leafRect?.width ?? width}
        height={leafRect?.height ?? height}
        fill="transparent"
        stroke="none"
      />
    </g>
  )
}

interface TooltipPayload {
  payload?: {
    name?: string
    value?: number
    stockName?: string
    country?: Country
    sectorName?: string
    weeklyChangeRate?: number | null
    plPercentage?: number | null
    symbol?: string
  }
}

function TreemapTooltip({
  active,
  payload,
  colorMetric,
}: {
  active?: boolean
  payload?: TooltipPayload[]
  colorMetric: ColorMetric
}) {
  if (!active || !payload?.length) return null
  const data = payload[0].payload
  if (!data?.symbol) return null
  return (
    <div className="rounded border border-border bg-background/95 px-3 py-2 text-sm shadow">
      <div className="font-semibold">{data.stockName || data.name}</div>
      <div className="text-xs text-muted-foreground">
        {data.country ? COUNTRY_LABELS[data.country] : ""} / {data.sectorName}
      </div>
      <div className="mt-1">評価額: {formatCurrency(data.value ?? 0)}</div>
      <div>
        {COLOR_METRIC_LABELS[colorMetric]}:{" "}
        {formatPercentOrDash(colorMetric === "weekly_change" ? data.weeklyChangeRate : data.plPercentage)}
      </div>
    </div>
  )
}

export function SectorTreemap({ data, isLoading, weeklyChangeMap }: SectorTreemapProps) {
  const navigate = useNavigate()
  const [countryFilter, setCountryFilter] = useState<CountryFilter>("ALL")
  const [colorMetric, setColorMetric] = useState<ColorMetric>("weekly_change")

  const treemapData = useMemo(
    () => transformHoldingsToTreemap(data, { country: countryFilter, colorMetric, weeklyChangeMap }),
    [data, countryFilter, colorMetric, weeklyChangeMap]
  )

  const colorScale = useMemo(() => computeColorScale(flattenColorValues(treemapData)), [treemapData])
  const colorMetricLabel = COLOR_METRIC_LABELS[colorMetric]

  const handleLeafClick = (symbol: string) => {
    navigate(`/holdings/${encodeURIComponent(symbol)}`)
  }

  const leafLayout = new Map<string, CellRect>()

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>セクター別ツリーマップ</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-96 animate-pulse rounded bg-muted" />
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>セクター別ツリーマップ</CardTitle>
        <p className="text-xs text-muted-foreground">面積: 評価額 / 色: {colorMetricLabel}</p>
        <div className="mt-3 space-y-2">
          <FilterRow
            label="国:"
            options={COUNTRY_FILTERS}
            value={countryFilter}
            onChange={setCountryFilter}
          />
          <FilterRow
            label="色:"
            options={COLOR_METRIC_OPTIONS}
            value={colorMetric}
            onChange={setColorMetric}
          />
        </div>
      </CardHeader>
      <CardContent>
        {treemapData.length === 0 ? (
          <div className="flex h-96 items-center justify-center text-muted-foreground">
            データがありません
          </div>
        ) : (
          <>
            <div className="h-96">
              <ResponsiveContainer width="100%" height="100%">
                <Treemap
                  data={treemapData as unknown as ReadonlyArray<{ [key: string]: unknown }>}
                  dataKey="value"
                  nameKey="name"
                  aspectRatio={4 / 3}
                  isAnimationActive={false}
                  content={
                    ((props: CellRenderProps) =>
                      renderTreemapCell(
                        props,
                        colorScale,
                        leafLayout,
                        handleLeafClick
                      )) as unknown as React.ReactElement
                  }
                >
                  <Tooltip content={<TreemapTooltip colorMetric={colorMetric} />} />
                </Treemap>
              </ResponsiveContainer>
            </div>
            <ColorLegend scale={colorScale} label={colorMetricLabel} />
          </>
        )}
      </CardContent>
    </Card>
  )
}

function ColorLegend({ scale, label }: { scale: ColorScale; label: string }) {
  const stops = useMemo(() => {
    const samples: number[] = []
    const steps = 7
    for (let i = 0; i <= steps; i++) {
      const ratio = i / steps
      samples.push(scale.minValue + (scale.maxValue - scale.minValue) * ratio)
    }
    return samples
  }, [scale])

  return (
    <div className="mt-3 flex flex-col gap-1 text-xs text-muted-foreground">
      <div className="flex items-center gap-2">
        <span>{label}</span>
        <div className="flex h-3 flex-1 overflow-hidden rounded">
          {stops.map((v) => (
            <div
              key={`stop-${v.toFixed(2)}`}
              className="flex-1"
              style={{ backgroundColor: getColorForValue(v, scale) }}
            />
          ))}
        </div>
        <span className="tabular-nums">
          {formatPercent(scale.minValue)} 〜 {formatPercent(scale.maxValue)}
        </span>
      </div>
      {(scale.outOfRangeAbove > 0 || scale.outOfRangeBelow > 0) && (
        <div>
          範囲外: 上限超過 {scale.outOfRangeAbove}銘柄 / 下限超過 {scale.outOfRangeBelow}銘柄
        </div>
      )}
    </div>
  )
}

interface FilterRowProps<T extends string> {
  label: string
  options: ReadonlyArray<{ value: T; label: string }>
  value: T
  onChange: (next: T) => void
}

function FilterRow<T extends string>({ label, options, value, onChange }: FilterRowProps<T>) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="text-xs text-muted-foreground">{label}</span>
      {options.map((opt) => (
        <Button
          key={opt.value}
          variant={value === opt.value ? "default" : "outline"}
          size="sm"
          onClick={() => onChange(opt.value)}
        >
          {opt.label}
        </Button>
      ))}
    </div>
  )
}
