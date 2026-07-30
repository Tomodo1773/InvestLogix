/**
 * 株式分割のドメインロジック
 *
 * 分割比率(split_ratio)は「分割前の1株が分割後に何株になるか」を表す。
 * 例: 4:1分割なら 4、1:2併合なら 0.5
 */

/** 分割比率を表示するときの最大小数桁数 */
const RATIO_MAX_FRACTION_DIGITS = 4

/** 浮動小数点の誤差を丸めて末尾のゼロを落とす */
function formatRatioNumber(value: number): string {
  return Number(value.toFixed(RATIO_MAX_FRACTION_DIGITS)).toString()
}

/**
 * 分割比率を「4:1 分割」「1:2 併合」の形式に整形する
 *
 * @param ratio 分割比率（分割前1株が分割後に何株になるか）
 * @returns 表示用の文字列。比率が不正な場合は "-"
 */
export function formatSplitRatio(ratio: number): string {
  if (!Number.isFinite(ratio) || ratio <= 0) {
    return "-"
  }
  if (ratio < 1) {
    return `1:${formatRatioNumber(1 / ratio)} 併合`
  }
  return `${formatRatioNumber(ratio)}:1 分割`
}

/**
 * 分割前後の株数から分割比率を求める
 *
 * 利用者に 0.5 のような比率を計算させずに済むよう、フォームでは株数で入力を受け取る。
 *
 * @param sharesBefore 分割前の株数
 * @param sharesAfter 分割後の株数
 * @returns 分割比率。株数が正の有限数でない場合は null
 */
export function splitRatioFromShares(sharesBefore: number, sharesAfter: number): number | null {
  if (!Number.isFinite(sharesBefore) || !Number.isFinite(sharesAfter)) {
    return null
  }
  if (sharesBefore <= 0 || sharesAfter <= 0) {
    return null
  }
  return sharesAfter / sharesBefore
}
