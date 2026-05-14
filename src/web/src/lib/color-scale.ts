/**
 * ツリーマップ用の動的カラースケール計算ユーティリティ。
 *
 * 値（損益率など）の分布から P5/P95 を求め、外れ値をクリップした
 * うえで 0% を中心に赤↔緑のグラデーションを作る。極端値を視覚的に
 * 黙殺せず「上限超過 N件」として呼び出し側で表示できるよう、
 * クリップ件数も返す。
 *
 * MVP では損益率（pl_percentage）のみサポート。将来的に
 * daily_change_percentage / dividend_yield を追加できるよう
 * メトリクス毎に floor/ceil/中心を選べる構造にしてある。
 */

type ColorMetric = "pl_percentage"

interface MetricConfig {
  /** 赤側下限（これより下にはクリップされない） */
  floor: number
  /** 緑側上限（これより上にはクリップされない） */
  ceil: number
  /** カラースケールの中心値（通常 0） */
  center: number
}

const METRIC_CONFIGS: Record<ColorMetric, MetricConfig> = {
  pl_percentage: { floor: -50, ceil: 100, center: 0 },
}

export interface ColorScale {
  metric: ColorMetric
  /** 赤側の最低値（負方向）。center より小さい */
  minValue: number
  /** 緑側の最高値（正方向）。center より大きい */
  maxValue: number
  /** 中心値 */
  centerValue: number
  /** クリップされた件数（上限を超えた銘柄数） */
  outOfRangeAbove: number
  /** クリップされた件数（下限を割った銘柄数） */
  outOfRangeBelow: number
}

/**
 * 昇順ソート済み配列からパーセンタイル値を線形補間で計算する。
 * 空配列のときは 0 を返す。
 */
export function percentile(sortedAsc: number[], p: number): number {
  if (sortedAsc.length === 0) return 0
  if (sortedAsc.length === 1) return sortedAsc[0]
  const clampedP = Math.max(0, Math.min(100, p))
  const rank = (clampedP / 100) * (sortedAsc.length - 1)
  const lower = Math.floor(rank)
  const upper = Math.ceil(rank)
  if (lower === upper) return sortedAsc[lower]
  const fraction = rank - lower
  return sortedAsc[lower] + (sortedAsc[upper] - sortedAsc[lower]) * fraction
}

/**
 * 値配列からカラースケールを計算する。
 *
 * - P5/P95 でレンジを決め、floor/ceil 内に収まるようクリップ
 * - 全プラスの相場でも minValue が center まで縮退しないよう、
 *   片側を必ず一定幅以上確保する（最低 5% を保証）
 */
export function computeColorScale(values: Array<number | null | undefined>, metric: ColorMetric): ColorScale {
  const config = METRIC_CONFIGS[metric]
  const validValues = values
    .filter((v): v is number => typeof v === "number" && Number.isFinite(v))
    .sort((a, b) => a - b)

  if (validValues.length === 0) {
    return {
      metric,
      minValue: config.floor,
      maxValue: config.ceil,
      centerValue: config.center,
      outOfRangeAbove: 0,
      outOfRangeBelow: 0,
    }
  }

  const rawMin = percentile(validValues, 5)
  const rawMax = percentile(validValues, 95)
  // 最低レンジ幅（片側 5%）を保証して、全プラス/全マイナスでも色味が出るようにする
  const MIN_HALF_RANGE = 5
  const minValue = Math.max(config.floor, Math.min(rawMin, config.center - MIN_HALF_RANGE))
  const maxValue = Math.min(config.ceil, Math.max(rawMax, config.center + MIN_HALF_RANGE))

  const outOfRangeAbove = validValues.filter((v) => v > maxValue).length
  const outOfRangeBelow = validValues.filter((v) => v < minValue).length

  return {
    metric,
    minValue,
    maxValue,
    centerValue: config.center,
    outOfRangeAbove,
    outOfRangeBelow,
  }
}

const NEUTRAL_COLOR = "#9CA3AF"
const POSITIVE_HUE = 142
const NEGATIVE_HUE = 0
const SATURATION = 65

/**
 * 値からカラーを取得する。中心値から離れるほど濃く、HSL で輝度を変化させる。
 * null/NaN は中立色を返す。
 */
export function getColorForValue(value: number | null | undefined, scale: ColorScale): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return NEUTRAL_COLOR
  }

  if (value >= scale.centerValue) {
    const range = scale.maxValue - scale.centerValue
    if (range <= 0) return NEUTRAL_COLOR
    const ratio = Math.max(0, Math.min(1, (value - scale.centerValue) / range))
    const lightness = 85 - ratio * 40
    return `hsl(${POSITIVE_HUE}, ${SATURATION}%, ${lightness}%)`
  }

  const range = scale.centerValue - scale.minValue
  if (range <= 0) return NEUTRAL_COLOR
  const ratio = Math.max(0, Math.min(1, (scale.centerValue - value) / range))
  const lightness = 85 - ratio * 40
  return `hsl(${NEGATIVE_HUE}, ${SATURATION}%, ${lightness}%)`
}
