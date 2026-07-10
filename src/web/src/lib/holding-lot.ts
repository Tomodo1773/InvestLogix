import type { Holding } from "@/lib/api/types"

const JAPANESE_STOCK_UNIT = 100
const JUNIOR_NISA_ACCOUNT_TYPE = "ジュニアNISA"

export interface UnitLotGroup {
  label: string
  quantity: number
}

export function isJapaneseStock(holding: Holding) {
  return holding.country === "JP" && holding.security_type === "STOCK"
}

export function getUnitLotGroups(holding: Holding): UnitLotGroup[] {
  let juniorNisaQuantity = 0
  let otherQuantity = 0

  for (const account of holding.account_holdings) {
    if (account.account_type === JUNIOR_NISA_ACCOUNT_TYPE) {
      juniorNisaQuantity += account.quantity
    } else {
      otherQuantity += account.quantity
    }
  }

  return [
    { label: JUNIOR_NISA_ACCOUNT_TYPE, quantity: juniorNisaQuantity },
    { label: "その他", quantity: otherQuantity },
  ].filter((group) => group.quantity > 0)
}

export function hasUnitLot(holding: Holding) {
  return (
    isJapaneseStock(holding) &&
    getUnitLotGroups(holding).some((group) => group.quantity >= JAPANESE_STOCK_UNIT)
  )
}

export function getLotStatusSortValue(holding: Holding) {
  if (!isJapaneseStock(holding)) return 0
  if (hasUnitLot(holding)) return 2
  return 1
}
