/**
 * ツリーマップ用カラースケール計算。
 *
 * 値（損益率）の P5/P95 でレンジを決め、0% を中心に赤↔緑のグラデーションを作る。
 * 全プラス／全マイナス相場でも色味が出るよう、片側を最低 ±5% は確保する。
 * 上限／下限を超えた外れ値は呼び出し側で「N件超過」として表示できるようカウントを返す。
 */

const FLOOR = -50
const CEIL = 100
const CENTER = 0
const MIN_HALF_RANGE = 5

const NEUTRAL_COLOR = "#9CA3AF"
const POSITIVE_HUE = 142
const NEGATIVE_HUE = 0
const SATURATION = 52

export interface ColorScale {
  minValue: number
  maxValue: number
  centerValue: number
  outOfRangeAbove: number
  outOfRangeBelow: number
}

/** 昇順ソート済み配列からパーセンタイル値を線形補間で計算する */
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

/** 昇順ソート済み配列で threshold より大きい最初のインデックスを返す（無ければ length） */
function firstIndexAbove(sortedAsc: number[], threshold: number): number {
  let lo = 0
  let hi = sortedAsc.length
  while (lo < hi) {
    const mid = (lo + hi) >> 1
    if (sortedAsc[mid] > threshold) hi = mid
    else lo = mid + 1
  }
  return lo
}

/** 昇順ソート済み配列で threshold より小さい最後のインデックス+1 を返す */
function countBelow(sortedAsc: number[], threshold: number): number {
  let lo = 0
  let hi = sortedAsc.length
  while (lo < hi) {
    const mid = (lo + hi) >> 1
    if (sortedAsc[mid] < threshold) lo = mid + 1
    else hi = mid
  }
  return lo
}

export function computeColorScale(values: Array<number | null | undefined>): ColorScale {
  const validValues = values
    .filter((v): v is number => typeof v === "number" && Number.isFinite(v))
    .sort((a, b) => a - b)

  if (validValues.length === 0) {
    return {
      minValue: FLOOR,
      maxValue: CEIL,
      centerValue: CENTER,
      outOfRangeAbove: 0,
      outOfRangeBelow: 0,
    }
  }

  const rawMin = percentile(validValues, 5)
  const rawMax = percentile(validValues, 95)
  const minValue = Math.max(FLOOR, Math.min(rawMin, CENTER - MIN_HALF_RANGE))
  const maxValue = Math.min(CEIL, Math.max(rawMax, CENTER + MIN_HALF_RANGE))

  return {
    minValue,
    maxValue,
    centerValue: CENTER,
    outOfRangeAbove: validValues.length - firstIndexAbove(validValues, maxValue),
    outOfRangeBelow: countBelow(validValues, minValue),
  }
}

export function getColorForValue(value: number | null | undefined, scale: ColorScale): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return NEUTRAL_COLOR
  }
  const isPositive = value >= scale.centerValue
  const hue = isPositive ? POSITIVE_HUE : NEGATIVE_HUE
  const range = isPositive ? scale.maxValue - scale.centerValue : scale.centerValue - scale.minValue
  if (range <= 0) return NEUTRAL_COLOR
  const distance = isPositive ? value - scale.centerValue : scale.centerValue - value
  const ratio = Math.max(0, Math.min(1, distance / range))
  const lightness = 88 - ratio * 36
  return `hsl(${hue}, ${SATURATION}%, ${lightness}%)`
}
