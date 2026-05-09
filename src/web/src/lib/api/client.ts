import type {
  Dividend,
  DividendImportConfirmRequest,
  DividendImportConfirmResponse,
  DividendImportPreviewResponse,
  Holding,
  ImportConfirmRequest,
  ImportConfirmResponse,
  ImportPreviewResponse,
  MonthlyDividendItem,
  MonthlySummaryItem,
  PortfolioHistoryItem,
  PortfolioSummary,
  PriceHistoryInterval,
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

export async function recalculateAllHoldings(): Promise<Holding[]> {
  return fetchWithAuth<Holding[]>("/api/v1/holdings/recalculate-all", {
    method: "POST",
  })
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

export async function updateHoldingNote(symbol: string, note: string | null): Promise<Holding> {
  return fetchWithAuth<Holding>(`/api/v1/holdings/${encodeURIComponent(symbol)}/note`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ note }),
  })
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
  interval: PriceHistoryInterval = "daily",
  limit: number = 80
): Promise<PriceHistoryResponse> {
  const params = new URLSearchParams({
    interval,
    limit: limit.toString(),
  })
  return fetchWithAuth<PriceHistoryResponse>(
    `/api/v1/symbols/${encodeURIComponent(symbol)}/price-history?${params.toString()}`
  )
}

// Stock Split APIs
export async function getStockSplits(symbol?: string): Promise<StockSplit[]> {
  const params = symbol ? `?symbol=${encodeURIComponent(symbol)}` : ""
  return fetchWithAuth<StockSplit[]>(`/api/v1/stock-splits/${params}`)
}

// CSV Import APIs
export async function uploadCsvForPreview(file: File): Promise<ImportPreviewResponse> {
  const formData = new FormData()
  formData.append("file", file)

  return fetchWithAuth<ImportPreviewResponse>("/api/v1/transactions/import/preview", {
    method: "POST",
    body: formData,
  })
}

export async function confirmImport(request: ImportConfirmRequest): Promise<ImportConfirmResponse> {
  return fetchWithAuth<ImportConfirmResponse>("/api/v1/transactions/import/confirm", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  })
}

// Dividend CSV Import APIs
export async function uploadDividendCsvForPreview(file: File): Promise<DividendImportPreviewResponse> {
  const formData = new FormData()
  formData.append("file", file)

  return fetchWithAuth<DividendImportPreviewResponse>("/api/v1/dividends/import/preview", {
    method: "POST",
    body: formData,
  })
}

export async function confirmDividendImport(
  request: DividendImportConfirmRequest
): Promise<DividendImportConfirmResponse> {
  return fetchWithAuth<DividendImportConfirmResponse>("/api/v1/dividends/import/confirm", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  })
}
