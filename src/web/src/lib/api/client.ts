import { useAuthStore } from "@/lib/stores/auth-store"
import type {
  Dividend,
  DividendBySymbolItem,
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
  StockSplitCreate,
  TokenResponse,
  Transaction,
  TransactionWithPL,
  User,
  WeeklyPerformanceResponse,
} from "./types"

// APIは常に同一オリジンの相対パスで叩く。本番はCloudflare Workerが、
// 開発時はViteのdev proxyが /api/* をバックエンドへ転送する。
// バックエンドのURLをバンドルに焼き込まないための設計。
// 同一オリジンなので認証Cookieは既定で送られる（credentials の指定は不要）
async function fetchWithAuth<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(endpoint, {
    ...options,
    headers: {
      ...options.headers,
    },
  })

  // 401はセッション切れ。ここでは認証状態を落とすだけにして、
  // ログイン画面への遷移はルータを持つAuthProviderに任せる
  // （window.location だとフルリロードになりSPAの状態を失う）
  if (response.status === 401) {
    useAuthStore.getState().setUser(null)
    throw new Error("セッションの有効期限が切れました")
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "An error occurred" }))
    throw new Error(typeof error.detail === "string" ? error.detail : "An error occurred")
  }

  return response.json()
}

/** JSONボディを送る書き込み系リクエスト（Content-Typeとシリアライズを共通化） */
async function sendJson<T>(endpoint: string, method: "POST" | "PUT", body: unknown): Promise<T> {
  return fetchWithAuth<T>(endpoint, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
}

// Auth APIs
export async function login(username: string, password: string): Promise<TokenResponse> {
  const response = await fetch("/api/v1/token", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      username,
      password,
    }),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Login failed" }))
    throw new Error(typeof error.detail === "string" ? error.detail : "Login failed")
  }

  return response.json()
}

// 認証Cookieはhttponlyなのでクライアントからは消せない。サーバーに削除させる。
// 204を返すのでボディのパースは行わない（fetchWithAuthは使えない）
export async function logout(): Promise<void> {
  const response = await fetch("/api/v1/logout", { method: "POST" })

  if (!response.ok) {
    throw new Error("Logout failed")
  }
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

export async function getWeeklyPerformance(): Promise<WeeklyPerformanceResponse> {
  return fetchWithAuth<WeeklyPerformanceResponse>("/api/v1/portfolio/weekly-performance")
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

export async function getDividendAllocation(params?: {
  year: number
  month: number
}): Promise<DividendBySymbolItem[]> {
  const query = params ? `?year=${params.year}&month=${params.month}` : ""
  return fetchWithAuth<DividendBySymbolItem[]>(`/api/v1/dividends/by-symbol${query}`)
}

// Symbol-specific APIs
export async function getHoldingBySymbol(symbol: string): Promise<Holding[]> {
  return fetchWithAuth<Holding[]>(`/api/v1/holdings/?symbol=${encodeURIComponent(symbol)}`)
}

export async function updateHoldingNote(symbol: string, note: string | null): Promise<Holding> {
  return sendJson<Holding>(`/api/v1/holdings/${encodeURIComponent(symbol)}/note`, "PUT", { note })
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

export async function createStockSplit(request: StockSplitCreate): Promise<StockSplit> {
  return sendJson<StockSplit>("/api/v1/stock-splits/", "POST", request)
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
  return sendJson<ImportConfirmResponse>("/api/v1/transactions/import/confirm", "POST", request)
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
  return sendJson<DividendImportConfirmResponse>("/api/v1/dividends/import/confirm", "POST", request)
}
