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
  user_id: number
  last_updated: string
  stock_name: string | null
}

// Transactions
export interface MonthlySummaryItem {
  year: number
  month: number
  total_purchase: Record<string, number>
}

// Dividends
export interface MonthlyDividendItem {
  year: number
  month: number
  total_dividend: number
}
