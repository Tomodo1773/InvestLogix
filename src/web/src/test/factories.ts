import type { Holding } from "@/lib/api/types"

/**
 * テスト用 Holding 生成ヘルパ。
 * 必要なフィールドだけ overrides で上書きする。
 */
export function createHolding(overrides: Partial<Holding> = {}): Holding {
  return {
    symbol: "TEST",
    quantity: 100,
    average_cost: 1000,
    total_cost: 100000,
    current_price: 1100,
    current_price_usd: null,
    market_value: 110000,
    market_value_usd: null,
    realized_pl: 0,
    total_dividend: 0,
    unrealized_pl: 10000,
    unrealized_pl_percentage: 10,
    total_pl: 10000,
    total_pl_percentage: 10,
    user_id: 1,
    last_updated: "2024-01-01",
    stock_name: "テスト",
    security_type: "STOCK",
    currency: "JPY",
    country: null,
    sector_name: null,
    note: null,
    ...overrides,
  }
}
