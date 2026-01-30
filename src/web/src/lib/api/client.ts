import type {
  Dividend,
  Holding,
  MonthlyDividendItem,
  MonthlySummaryItem,
  PortfolioHistoryItem,
  PortfolioSummary,
  PriceHistoryInterval,
  PriceHistoryPeriod,
  PriceHistoryResponse,
  Stock,
  StockSplit,
  TokenResponse,
  Transaction,
  TransactionWithPL,
  User,
} from "./types"

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000"

async function fetchWithAuth<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    credentials: "include",
    headers: {
      ...options.headers,
    },
  })

  if (response.status === 401) {
    window.location.href = "/login"
    throw new Error("Unauthorized")
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "An error occurred" }))
    throw new Error(typeof error.detail === "string" ? error.detail : "An error occurred")
  }

  return response.json()
}

// Auth APIs
export async function login(username: string, password: string): Promise<TokenResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/token`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      username,
      password,
    }),
    credentials: "include",
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Login failed" }))
    throw new Error(typeof error.detail === "string" ? error.detail : "Login failed")
  }

  return response.json()
}

export async function getCurrentUser(): Promise<User> {
  return fetchWithAuth<User>("/api/v1/me")
}

// Portfolio APIs
export async function getPortfolioSummary(): Promise<PortfolioSummary> {
  return fetchWithAuth<PortfolioSummary>("/api/v1/portfolio/summary")
}

export async function getPortfolioHistory(): Promise<PortfolioHistoryItem[]> {
  return fetchWithAuth<PortfolioHistoryItem[]>("/api/v1/portfolio/history")
}

export async function getHoldings(): Promise<Holding[]> {
  return fetchWithAuth<Holding[]>("/api/v1/holdings/")
}

// Transaction APIs
export async function getTransactions(): Promise<Transaction[]> {
  return fetchWithAuth<Transaction[]>("/api/v1/transactions/")
}

export async function getTransactionsMonthlySummary(): Promise<MonthlySummaryItem[]> {
  return fetchWithAuth<MonthlySummaryItem[]>("/api/v1/transactions/monthly-summary")
}

// Dividend APIs
export async function getDividends(): Promise<Dividend[]> {
  return fetchWithAuth<Dividend[]>("/api/v1/dividends/")
}

export async function getDividendsMonthly(): Promise<MonthlyDividendItem[]> {
  return fetchWithAuth<MonthlyDividendItem[]>("/api/v1/dividends/monthly")
}

// Symbol-specific APIs
export async function getHoldingBySymbol(symbol: string): Promise<Holding[]> {
  return fetchWithAuth<Holding[]>(`/api/v1/holdings/?symbol=${encodeURIComponent(symbol)}`)
}

export async function getTransactionsBySymbol(symbol: string): Promise<TransactionWithPL[]> {
  return fetchWithAuth<TransactionWithPL[]>(
    `/api/v1/transactions/?symbol=${encodeURIComponent(symbol)}&include_unrealized_pl=true`
  )
}

export async function getDividendsBySymbol(symbol: string): Promise<Dividend[]> {
  return fetchWithAuth<Dividend[]>(`/api/v1/dividends/?symbol=${encodeURIComponent(symbol)}`)
}

// Stock APIs
export async function getStocks(market?: string): Promise<Stock[]> {
  const params = market ? `?market=${encodeURIComponent(market)}` : ""
  return fetchWithAuth<Stock[]>(`/api/v1/stocks/${params}`)
}

// Price History API
export async function getPriceHistory(
  symbol: string,
  period: PriceHistoryPeriod = "1Y",
  interval: PriceHistoryInterval = "daily"
): Promise<PriceHistoryResponse> {
  const params = new URLSearchParams({
    period,
    interval,
  })
  return fetchWithAuth<PriceHistoryResponse>(
    `/api/v1/stocks/${encodeURIComponent(symbol)}/price-history?${params.toString()}`
  )
}

// Stock Split APIs
export async function getStockSplits(symbol?: string): Promise<StockSplit[]> {
  const params = symbol ? `?symbol=${encodeURIComponent(symbol)}` : ""
  return fetchWithAuth<StockSplit[]>(`/api/v1/stock-splits/${params}`)
}
