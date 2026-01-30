// Auth
export interface TokenResponse {
  access_token: string
  token_type: string
}

export interface User {
  user_id: number
  username: string
  email: string
  created_at: string
  line_user_id: string | null
  is_admin: boolean
}

// Portfolio
export interface PortfolioSummary {
  total_cost: string
  total_market_value: string
  total_unrealized_pl: string
  total_unrealized_pl_percentage: string
  total_realized_pl: string
  total_dividend: string
  total_pl: string
  total_pl_percentage: string
  holdings_by_market: Record<string, string>
  holdings_by_currency: Record<string, string>
}

export interface PortfolioHistoryItem {
  date: string
  total_cost: number
  total_market_value: number
  total_unrealized_pl: number
  total_unrealized_pl_percentage: number
  total_realized_pl: number
  total_dividend: number
  total_pl: number
  total_pl_percentage: number
}

export interface Holding {
  symbol: string
  quantity: string
  average_cost: string
  total_cost: string
  current_price: string | null
  market_value: string | null
  realized_pl: string | null
  total_dividend: string | null
  unrealized_pl: string | null
  unrealized_pl_percentage: string | null
  total_pl: string | null
  total_pl_percentage: string | null
  user_id: number
  last_updated: string
  stock_name: string | null
  security_type: string | null
  currency: string | null
}

// Transactions
export interface MonthlySummaryItem {
  year: number
  month: number
  total_purchase: Record<string, number>
}

// Transactions
export type AccountType = "NISA(成長投資枠)" | "NISA(つみたて投資枠)" | "ジュニアNISA" | "旧NISA" | "特定"

export interface Transaction {
  symbol: string
  transaction_type: "buy" | "sell"
  quantity: string
  price: string
  usd_price: string | null
  adjusted_price: string | null
  adjusted_quantity: string | null
  account_type: AccountType
  fee: string
  tax: string
  realized_pl: string | null
  transaction_id: number
  user_id: number
  transaction_date: string
  stock_name: string | null
}

export interface TransactionWithPL extends Transaction {
  unrealized_pl: string | null
  unrealized_pl_percentage: string | null
}

// Dividends
export interface Dividend {
  symbol: string
  payment_date: string
  shares_owned: string
  total_amount: string
  tax: string | null
  fee: string | null
  dividend_id: number
  user_id: number
  stock_name: string | null
}

export interface MonthlyDividendItem {
  year: number
  month: number
  total_dividend: number
}

// Stocks
export type SecurityType = "STOCK" | "ETF" | "REIT" | "FUND"

export interface Stock {
  symbol: string
  name: string
  name_en: string | null
  market: string
  security_type: SecurityType
  currency: string
  last_updated: string
}

// Price History
export type PriceHistoryInterval = "daily" | "weekly" | "monthly"

export interface PriceDataPoint {
  date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export interface PriceHistoryResponse {
  symbol: string
  interval: string
  data: PriceDataPoint[]
}

// Stock Splits
export interface StockSplit {
  split_id: number
  user_id: number
  symbol: string
  split_date: string
  split_ratio: string
  created_at: string
}
