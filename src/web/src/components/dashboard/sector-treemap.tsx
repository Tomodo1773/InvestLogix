import { useMemo, useState } from "react"
import { useNavigate } from "react-router"
import { ResponsiveContainer, Tooltip, Treemap } from "recharts"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { Holding } from "@/lib/api/types"
import { type ColorScale, computeColorScale, getColorForValue } from "@/lib/color-scale"
import { formatCurrency, formatPercent } from "@/lib/format"

type CountryFilter = "ALL" | "JP" | "US" | "OTHER"
type SecurityTypeFilter = "ALL" | "STOCK" | "ETF" | "FUND" | "REIT"

interface SectorTreemapProps {
  data: Holding[] | undefined
  isLoading: boolean
}

interface TreemapLeaf {
  name: string
  value: number
  symbol: string
  stockName: string
  country: string
  sectorName: string
  plPercentage: number | null
  [key: string]: unknown
}

interface TreemapSector {
  name: string
  children: TreemapLeaf[]
  [key: string]: unknown
}

interface TreemapCountry {
  name: string
  children: TreemapSector[]
  [key: string]: unknown
}

const COUNTRY_FILTERS: { value: CountryFilter; label: string }[] = [
  { value: "ALL", label: "すべて" },
  { value: "JP", label: "日本" },
  { value: "US", label: "米国" },
  { value: "OTHER", label: "その他" },
]

const SECURITY_TYPE_FILTERS: { value: SecurityTypeFilter; label: string }[] = [
  { value: "ALL", label: "すべて" },
  { value: "STOCK", label: "株式" },
  { value: "ETF", label: "ETF" },
  { value: "FUND", label: "投信" },
  { value: "REIT", label: "REIT" },
]

const COUNTRY_LABELS: Record<string, string> = {
  JP: "日本",
  US: "米国",
  OTHER: "その他",
}

/**
 * 保有銘柄を国 → セクター → 銘柄の3階層ツリーマップ用データに変換する。
 * 評価額（market_value）が 0 以下の銘柄、フィルタ条件に合わない銘柄は除外。
 * country/sector_name が null のものは "OTHER"/"その他" に集約する。
 */
export function transformHoldingsToTreemap(
  holdings: Holding[] | undefined,
  filters: { country: CountryFilter; securityType: SecurityTypeFilter }
): TreemapCountry[] {
  if (!holdings || holdings.length === 0) return []

  const filtered = holdings.filter((h) => {
    if ((h.market_value ?? 0) <= 0) return false
    const countryKey = h.country ?? "OTHER"
    if (filters.country !== "ALL" && countryKey !== filters.country) return false
    if (filters.securityType !== "ALL" && h.security_type !== filters.securityType) return false
    return true
  })

  const byCountry = new Map<string, Map<string, TreemapLeaf[]>>()
  for (const h of filtered) {
    const countryKey = h.country ?? "OTHER"
    const sectorKey = h.sector_name ?? "その他"
    if (!byCountry.has(countryKey)) byCountry.set(countryKey, new Map())
    const sectors = byCountry.get(countryKey)
    if (!sectors) continue
    if (!sectors.has(sectorKey)) sectors.set(sectorKey, [])
    const leaves = sectors.get(sectorKey)
    if (!leaves) continue
    leaves.push({
      name: h.stock_name || h.symbol,
      value: h.market_value ?? 0,
      symbol: h.symbol,
      stockName: h.stock_name || h.symbol,
      country: countryKey,
      sectorName: sectorKey,
      plPercentage: h.unrealized_pl_percentage,
    })
  }

  const result: TreemapCountry[] = []
  for (const [countryKey, sectors] of byCountry.entries()) {
    const sectorBranches: TreemapSector[] = []
    for (const [sectorName, leaves] of sectors.entries()) {
      leaves.sort((a, b) => b.value - a.value)
      sectorBranches.push({ name: sectorName, children: leaves })
    }
    sectorBranches.sort((a, b) => sumLeafValues(b.children) - sumLeafValues(a.children))
    result.push({ name: COUNTRY_LABELS[countryKey] ?? countryKey, children: sectorBranches })
  }
  const countryTotal = (c: TreemapCountry) =>
    c.children.reduce((s, sec) => s + sumLeafValues(sec.children), 0)
  result.sort((a, b) => countryTotal(b) - countryTotal(a))
  return result
}

function sumLeafValues(leaves: TreemapLeaf[]): number {
  return leaves.reduce((sum, l) => sum + l.value, 0)
}

/** カラースケール計算用に leaf の損益率を平らな配列で取り出す */
export function flattenColorValues(data: TreemapCountry[]): Array<number | null> {
  const out: Array<number | null> = []
  for (const country of data) {
    for (const sector of country.children) {
      for (const leaf of sector.children) {
        out.push(leaf.plPercentage)
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
  plPercentage?: number | null
  symbol?: string
}

function renderTreemapCell(props: CellRenderProps, scale: ColorScale, onLeafClick: (symbol: string) => void) {
  const { x = 0, y = 0, width = 0, height = 0, depth = 0, name, plPercentage, symbol } = props
  const isLeaf = depth >= 2 && !!symbol
  const fill = isLeaf ? getColorForValue(plPercentage ?? null, scale) : "transparent"
  const showLabel = width > 60 && height > 24

  if (isLeaf && symbol) {
    return (
      <g
        role="button"
        tabIndex={0}
        style={{ cursor: "pointer" }}
        onClick={() => onLeafClick(symbol)}
        onKeyDown={(e: React.KeyboardEvent<SVGGElement>) => {
          if (e.key === "Enter" || e.key === " ") onLeafClick(symbol)
        }}
      >
        <rect x={x} y={y} width={width} height={height} fill={fill} stroke="#ffffff" strokeWidth={1} />
        {showLabel && (
          <text x={x + 4} y={y + 14} fill="#111827" fontSize={11} fontWeight={500}>
            {name}
          </text>
        )}
      </g>
    )
  }
  return (
    <g>
      <rect
        x={x}
        y={y}
        width={width}
        height={height}
        fill="transparent"
        stroke={depth === 1 ? "#1f2937" : "#ffffff"}
        strokeWidth={depth === 1 ? 2 : 1}
      />
    </g>
  )
}

interface TooltipPayload {
  payload?: {
    name?: string
    value?: number
    stockName?: string
    country?: string
    sectorName?: string
    plPercentage?: number | null
    symbol?: string
  }
}

function TreemapTooltip({ active, payload }: { active?: boolean; payload?: TooltipPayload[] }) {
  if (!active || !payload?.length) return null
  const data = payload[0].payload
  if (!data?.symbol) return null
  return (
    <div className="rounded border border-border bg-background/95 px-3 py-2 text-sm shadow">
      <div className="font-semibold">{data.stockName || data.name}</div>
      <div className="text-xs text-muted-foreground">
        {COUNTRY_LABELS[data.country ?? ""] ?? data.country} / {data.sectorName}
      </div>
      <div className="mt-1">評価額: {formatCurrency(data.value ?? 0)}</div>
      <div>損益率: {formatPercent(data.plPercentage ?? null)}</div>
    </div>
  )
}

export function SectorTreemap({ data, isLoading }: SectorTreemapProps) {
  const navigate = useNavigate()
  const [countryFilter, setCountryFilter] = useState<CountryFilter>("ALL")
  const [securityTypeFilter, setSecurityTypeFilter] = useState<SecurityTypeFilter>("ALL")

  const treemapData = useMemo(
    () => transformHoldingsToTreemap(data, { country: countryFilter, securityType: securityTypeFilter }),
    [data, countryFilter, securityTypeFilter]
  )

  const colorScale = useMemo(
    () => computeColorScale(flattenColorValues(treemapData), "pl_percentage"),
    [treemapData]
  )

  const handleLeafClick = (symbol: string) => {
    navigate(`/holdings/${encodeURIComponent(symbol)}`)
  }

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
        <div className="mt-3 space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs text-muted-foreground">国:</span>
            {COUNTRY_FILTERS.map((opt) => (
              <Button
                key={opt.value}
                variant={countryFilter === opt.value ? "default" : "outline"}
                size="sm"
                onClick={() => setCountryFilter(opt.value)}
              >
                {opt.label}
              </Button>
            ))}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs text-muted-foreground">種別:</span>
            {SECURITY_TYPE_FILTERS.map((opt) => (
              <Button
                key={opt.value}
                variant={securityTypeFilter === opt.value ? "default" : "outline"}
                size="sm"
                onClick={() => setSecurityTypeFilter(opt.value)}
              >
                {opt.label}
              </Button>
            ))}
          </div>
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
                  data={treemapData}
                  dataKey="value"
                  nameKey="name"
                  aspectRatio={4 / 3}
                  isAnimationActive={false}
                  content={
                    ((props: CellRenderProps) =>
                      renderTreemapCell(props, colorScale, handleLeafClick)) as never
                  }
                >
                  <Tooltip content={<TreemapTooltip />} />
                </Treemap>
              </ResponsiveContainer>
            </div>
            <ColorLegend scale={colorScale} />
          </>
        )}
      </CardContent>
    </Card>
  )
}

function ColorLegend({ scale }: { scale: ColorScale }) {
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
        <span>損益率</span>
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
