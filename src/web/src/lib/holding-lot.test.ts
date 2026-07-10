import { describe, expect, it } from "vitest"
import { createHolding } from "@/test/factories"
import { getLotStatusSortValue, getUnitLotGroups, hasUnitLot } from "./holding-lot"

describe("holding-lot", () => {
  it("ジュニアNISA以外の数量を合算して単元判定する", () => {
    const holding = createHolding({
      country: "JP",
      security_type: "STOCK",
      account_holdings: [
        { account_type: "NISA(成長投資枠)", quantity: 80 },
        { account_type: "特定", quantity: 20 },
      ],
    })

    expect(getUnitLotGroups(holding)).toEqual([{ label: "その他", quantity: 100 }])
    expect(hasUnitLot(holding)).toBe(true)
    expect(getLotStatusSortValue(holding)).toBe(2)
  })

  it("ジュニアNISAはその他口座と合算しない", () => {
    const holding = createHolding({
      country: "JP",
      security_type: "STOCK",
      account_holdings: [
        { account_type: "ジュニアNISA", quantity: 50 },
        { account_type: "特定", quantity: 50 },
      ],
    })

    expect(getUnitLotGroups(holding)).toEqual([
      { label: "ジュニアNISA", quantity: 50 },
      { label: "その他", quantity: 50 },
    ])
    expect(hasUnitLot(holding)).toBe(false)
    expect(getLotStatusSortValue(holding)).toBe(1)
  })

  it("日本株以外は単元判定の対象外にする", () => {
    const holding = createHolding({
      country: "US",
      security_type: "STOCK",
      account_holdings: [{ account_type: "特定", quantity: 100 }],
    })

    expect(hasUnitLot(holding)).toBe(false)
    expect(getLotStatusSortValue(holding)).toBe(0)
  })
})
