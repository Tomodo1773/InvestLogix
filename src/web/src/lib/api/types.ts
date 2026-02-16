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
  total_cost: number
  total_market_value: number
  total_unrealized_pl: number
  total_unrealized_pl_percentage: number
  total_realized_pl: number
  total_dividend: number
  total_pl: number
  total_pl_percentage: number
  holdings_by_market: Record<string, number>
  holdings_by_currency: Record<string, number>
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
  quantity: number
  average_cost: number
  total_cost: number
  current_price: number | null
  market_value: number | null
  realized_pl: number | null
  total_dividend: number | null
  unrealized_pl: number | null
  unrealized_pl_percentage: number | null
  total_pl: number | null
  total_pl_percentage: number | null
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
  quantity: number
  price: number
  usd_price: number | null
  adjusted_price: number | null
  adjusted_quantity: number | null
  account_type: AccountType
  fee: number
  tax: number
  realized_pl: number | null
  transaction_id: number
  user_id: number
  transaction_date: string
  stock_name: string | null
}

export interface TransactionWithPL extends Transaction {
  unrealized_pl: number | null
  unrealized_pl_percentage: number | null
}

// Dividends
export interface Dividend {
  symbol: string
  payment_date: string
  shares_owned: number
  total_amount: number
  tax: number | null
  fee: number | null
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
  split_ratio: number
  created_at: string
  stock_name: string | null
}

// CSV Import
export interface CsvTransactionPreview {
  symbol: string
  name: string
  transaction_type: "buy" | "sell"
  quantity: number
  price: number
  usd_price: number | null
  account_type: AccountType
  fee: number
  tax: number
  transaction_date: string
}

export interface ImportPreviewResponse {
  new_transactions: CsvTransactionPreview[]
  existing_count: number
  csv_total_count: number
  skipped_count: number
  errors: string[]
}

export interface ImportConfirmRequest {
  transactions: {
    symbol: string
    transaction_type: "buy" | "sell"
    quantity: number
    price: number
    usd_price: number | null
    account_type: AccountType
    fee: number
    tax: number
    transaction_date: string
  }[]
}

export interface ImportConfirmResponse {
  created_count: number
  failed_count: number
  errors: string[]
}

// Dividend CSV Import
export interface CsvDividendPreview {
  symbol: string
  name: string
  payment_date: string
  shares_owned: number
  total_amount: number
}

export interface DividendImportPreviewResponse {
  new_dividends: CsvDividendPreview[]
  existing_count: number
  csv_total_count: number
  skipped_count: number
  errors: string[]
}

export interface DividendImportConfirmRequest {
  dividends: {
    symbol: string
    payment_date: string
    shares_owned: number
    total_amount: number
    tax: number
    fee: number
  }[]
}

export interface DividendImportConfirmResponse {
  created_count: number
  failed_count: number
  errors: string[]
}
