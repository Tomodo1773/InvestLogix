/**
 * SWRのキャッシュキー
 *
 * 各画面が個別に文字列を書くと、同じリソースが別キーで二重にキャッシュされたり
 * （例: 資産推移がダッシュボードと専用ページで別キーだった）、
 * 更新系の処理から「どのキャッシュを落とすべきか」を表明できなくなる。
 * キーはここだけで定義する。
 */
export const SWR_KEYS = {
  portfolioSummary: "/api/v1/portfolio/summary",
  portfolioHistory: "/api/v1/portfolio/history",
  weeklyPerformance: "/api/v1/portfolio/weekly-performance",
  holdings: "/api/v1/holdings/",
  transactions: "/api/v1/transactions/",
  transactionsMonthly: "/api/v1/transactions/monthly-summary",
  dividends: "/api/v1/dividends/",
  dividendsMonthly: "/api/v1/dividends/monthly",
  stocks: "/api/v1/stocks/",
  stockSplits: "/api/v1/stock-splits/",

  holdingBySymbol: (symbol: string) => `/api/v1/holdings/?symbol=${symbol}`,
  transactionsBySymbol: (symbol: string) => `/api/v1/transactions/?symbol=${symbol}`,
  dividendsBySymbol: (symbol: string) => `/api/v1/dividends/?symbol=${symbol}`,
  stockSplitsBySymbol: (symbol: string) => `/api/v1/stock-splits/?symbol=${symbol}`,
  priceHistory: (symbol: string, interval: string, limit: number) =>
    `/api/v1/symbols/${symbol}/price-history?interval=${interval}&limit=${limit}`,
  /** 期間で絞り込むため配列キーを使う。refreshSignalは明示的な再取得のトリガ */
  dividendAllocation: (period: string, refreshSignal: number) =>
    ["/api/v1/dividends/by-symbol", period, refreshSignal] as const,
} as const
