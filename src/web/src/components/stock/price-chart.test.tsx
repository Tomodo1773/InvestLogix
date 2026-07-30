import { render, screen } from "@testing-library/react"
import { userEvent } from "@testing-library/user-event"
import { describe, expect, it, vi } from "vitest"
import type { PriceHistoryResponse } from "@/lib/api/types"
import { PriceChart } from "./price-chart"

// SWRをモック化
vi.mock("swr", () => ({
  default: vi.fn(() => {
    // デフォルトのモック実装
    return {
      data: undefined,
      isLoading: false,
      error: null,
    }
  }),
}))

// Rechartsをモック化（グラフライブラリ自体のテストは不要）
// ただし、XAxisのpropsは保存してテスト可能にする
type CapturedXAxisProps = {
  ticks?: number[]
  tickFormatter?: (value: number) => string
}

let capturedXAxisProps: CapturedXAxisProps | null = null

vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="recharts-container">{children}</div>
  ),
  LineChart: ({ children }: { children: React.ReactNode }) => <div data-testid="line-chart">{children}</div>,
  Line: () => <div data-testid="line" />,
  XAxis: (props: CapturedXAxisProps) => {
    capturedXAxisProps = props
    return <div data-testid="x-axis" />
  },
  YAxis: () => <div data-testid="y-axis" />,
  CartesianGrid: () => <div data-testid="cartesian-grid" />,
  Tooltip: () => <div data-testid="tooltip" />,
  ReferenceLine: () => <div data-testid="reference-line" />,
}))

const mockPriceData: PriceHistoryResponse = {
  symbol: "7203",
  interval: "daily",
  data: [
    {
      date: "2025-01-20",
      open: 3000,
      high: 3050,
      low: 2980,
      close: 3020,
      volume: 1000000,
    },
    {
      date: "2025-01-21",
      open: 3020,
      high: 3080,
      low: 3010,
      close: 3060,
      volume: 1200000,
    },
  ],
}

const toMs = (date: string) => new Date(date).getTime()
const getCapturedXAxisProps = () => {
  if (!capturedXAxisProps) {
    throw new Error("XAxis propsが取得できませんでした")
  }
  return capturedXAxisProps
}

describe("PriceChart", () => {
  it("投資信託の場合は非表示になること", () => {
    const { container } = render(<PriceChart symbol="12345" securityType="FUND" />)
    expect(container.firstChild).toBeNull()
  })

  it("期間切り替えボタンが表示されないこと", async () => {
    const useSWR = await import("swr")
    vi.mocked(useSWR.default).mockReturnValue({
      data: mockPriceData,
      isLoading: false,
      error: null,
      isValidating: false,
      mutate: vi.fn(),
    })

    render(<PriceChart symbol="7203" securityType="STOCK" />)

    // 期間ボタンは削除されたため表示されないこと
    expect(screen.queryByText("1M")).not.toBeInTheDocument()
    expect(screen.queryByText("3M")).not.toBeInTheDocument()
    expect(screen.queryByText("6M")).not.toBeInTheDocument()
    expect(screen.queryByText("1Y")).not.toBeInTheDocument()
    expect(screen.queryByText("3Y")).not.toBeInTheDocument()
  })

  it("間隔切り替えボタンが表示されること", async () => {
    const useSWR = await import("swr")
    vi.mocked(useSWR.default).mockReturnValue({
      data: mockPriceData,
      isLoading: false,
      error: null,
      isValidating: false,
      mutate: vi.fn(),
    })

    render(<PriceChart symbol="7203" securityType="STOCK" />)

    // 間隔ボタンが表示されること
    expect(screen.getByText("日足")).toBeInTheDocument()
    expect(screen.getByText("週足")).toBeInTheDocument()
    expect(screen.getByText("月足")).toBeInTheDocument()
  })

  it("エラー時にエラーメッセージが表示されること", async () => {
    const useSWR = await import("swr")
    vi.mocked(useSWR.default).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error("API Error"),
      isValidating: false,
      mutate: vi.fn(),
    })

    render(<PriceChart symbol="7203" securityType="STOCK" />)

    expect(screen.getByText("データを取得できませんでした")).toBeInTheDocument()
  })

  it("データが空の場合にメッセージが表示されること", async () => {
    const useSWR = await import("swr")
    vi.mocked(useSWR.default).mockReturnValue({
      data: { symbol: "7203", interval: "daily", data: [] },
      isLoading: false,
      error: null,
      isValidating: false,
      mutate: vi.fn(),
    })

    render(<PriceChart symbol="7203" securityType="STOCK" />)

    expect(screen.getByText("データがありません")).toBeInTheDocument()
  })

  it("間隔ボタンをクリックすると選択状態が変わること", async () => {
    const user = userEvent.setup()
    const useSWR = await import("swr")
    vi.mocked(useSWR.default).mockReturnValue({
      data: mockPriceData,
      isLoading: false,
      error: null,
      isValidating: false,
      mutate: vi.fn(),
    })

    render(<PriceChart symbol="7203" securityType="STOCK" />)

    const buttonWeekly = screen.getByText("週足")

    // 初期状態では日足が選択されている
    const buttonDaily = screen.getByText("日足")
    expect(buttonDaily).toHaveClass("bg-primary")

    // 週足ボタンをクリック
    await user.click(buttonWeekly)

    // 週足が選択状態になる
    expect(buttonWeekly).toHaveClass("bg-primary")
  })

  describe("X軸ティック計算とフォーマット", () => {
    it("日足の場合、月変わりの最初のデータポイントがティックになる", async () => {
      const useSWR = await import("swr")
      const dailyData: PriceHistoryResponse = {
        symbol: "7203",
        interval: "daily",
        data: [
          { date: "2025-11-28", open: 3000, high: 3050, low: 2980, close: 3020, volume: 1000000 },
          { date: "2025-11-30", open: 3020, high: 3080, low: 3010, close: 3060, volume: 1200000 },
          { date: "2025-12-06", open: 3060, high: 3100, low: 3040, close: 3080, volume: 1100000 },
          { date: "2025-12-08", open: 3080, high: 3120, low: 3070, close: 3100, volume: 1300000 },
        ],
      }

      vi.mocked(useSWR.default).mockReturnValue({
        data: dailyData,
        isLoading: false,
        error: null,
        isValidating: false,
        mutate: vi.fn(),
      })

      render(<PriceChart symbol="7203" securityType="STOCK" />)

      // XAxisのpropsを取得
      const { ticks, tickFormatter } = getCapturedXAxisProps()
      if (!tickFormatter) {
        throw new Error("tickFormatterが取得できませんでした")
      }

      // ティックは月変わりの最初のデータポイントのみ
      expect(ticks).toEqual([toMs("2025-11-28"), toMs("2025-12-06")])

      // 最初のデータポイントは年月表示
      expect(tickFormatter(toMs("2025-11-28"))).toBe("2025/11")
      // 同じ年の月変わりは月のみ表示
      expect(tickFormatter(toMs("2025-12-06"))).toBe("12")
    })

    it("日足で年が変わる場合、年変わりの月はyyyy/mm形式で表示される", async () => {
      const useSWR = await import("swr")
      const dailyData: PriceHistoryResponse = {
        symbol: "7203",
        interval: "daily",
        data: [
          { date: "2024-11-01", open: 3000, high: 3050, low: 2980, close: 3020, volume: 1000000 },
          { date: "2024-11-15", open: 3020, high: 3080, low: 3010, close: 3060, volume: 1200000 },
          { date: "2024-12-02", open: 3060, high: 3100, low: 3040, close: 3080, volume: 1100000 },
          { date: "2025-01-06", open: 3080, high: 3120, low: 3070, close: 3100, volume: 1300000 },
        ],
      }

      vi.mocked(useSWR.default).mockReturnValue({
        data: dailyData,
        isLoading: false,
        error: null,
        isValidating: false,
        mutate: vi.fn(),
      })

      render(<PriceChart symbol="7203" securityType="STOCK" />)

      const { ticks, tickFormatter } = getCapturedXAxisProps()
      if (!tickFormatter) {
        throw new Error("tickFormatterが取得できませんでした")
      }

      // ティックは月変わりのみ
      expect(ticks).toEqual([toMs("2024-11-01"), toMs("2024-12-02"), toMs("2025-01-06")])

      // 最初のデータポイント
      expect(tickFormatter(toMs("2024-11-01"))).toBe("2024/11")
      // 同じ年の月変わり
      expect(tickFormatter(toMs("2024-12-02"))).toBe("12")
      // 年が変わった月
      expect(tickFormatter(toMs("2025-01-06"))).toBe("2025/01")
    })

    it("週足の場合、四半期開始月（1,4,7,10月）の最初のデータポイントがティックになる", async () => {
      const useSWR = await import("swr")
      const weeklyData: PriceHistoryResponse = {
        symbol: "7203",
        interval: "weekly",
        data: [
          { date: "2024-12-30", open: 3000, high: 3050, low: 2980, close: 3020, volume: 5000000 },
          { date: "2025-01-06", open: 3020, high: 3080, low: 3010, close: 3060, volume: 6000000 },
          { date: "2025-01-13", open: 3060, high: 3100, low: 3040, close: 3080, volume: 5500000 },
          { date: "2025-02-03", open: 3080, high: 3120, low: 3070, close: 3100, volume: 6500000 },
          { date: "2025-04-07", open: 3100, high: 3150, low: 3090, close: 3120, volume: 6200000 },
        ],
      }

      vi.mocked(useSWR.default).mockReturnValue({
        data: weeklyData,
        isLoading: false,
        error: null,
        isValidating: false,
        mutate: vi.fn(),
      })

      render(<PriceChart symbol="7203" securityType="STOCK" />)

      const buttonWeekly = screen.getByText("週足")
      await userEvent.setup().click(buttonWeekly)

      const { ticks, tickFormatter } = getCapturedXAxisProps()
      if (!tickFormatter) {
        throw new Error("tickFormatterが取得できませんでした")
      }

      // ティックは最初と四半期開始月（1,4月）のみ
      expect(ticks).toEqual([toMs("2024-12-30"), toMs("2025-01-06"), toMs("2025-04-07")])

      // 最初のデータポイント
      expect(tickFormatter(toMs("2024-12-30"))).toBe("2024/12")
      // 1月（年が変わっているのでyyyy/mm）
      expect(tickFormatter(toMs("2025-01-06"))).toBe("2025/01")
      // 4月（同じ年なのでmm）
      expect(tickFormatter(toMs("2025-04-07"))).toBe("04")
    })

    it("月足の場合、1月のみがティックになる", async () => {
      const useSWR = await import("swr")
      const monthlyData: PriceHistoryResponse = {
        symbol: "7203",
        interval: "monthly",
        data: [
          { date: "2024-01-01", open: 3000, high: 3050, low: 2980, close: 3020, volume: 20000000 },
          { date: "2024-06-01", open: 3020, high: 3080, low: 3010, close: 3060, volume: 24000000 },
          { date: "2024-12-01", open: 3040, high: 3090, low: 3020, close: 3070, volume: 23000000 },
          { date: "2025-01-01", open: 3060, high: 3100, low: 3040, close: 3080, volume: 22000000 },
        ],
      }

      vi.mocked(useSWR.default).mockReturnValue({
        data: monthlyData,
        isLoading: false,
        error: null,
        isValidating: false,
        mutate: vi.fn(),
      })

      render(<PriceChart symbol="7203" securityType="STOCK" />)

      const buttonMonthly = screen.getByText("月足")
      await userEvent.setup().click(buttonMonthly)

      const { ticks, tickFormatter } = getCapturedXAxisProps()
      if (!tickFormatter) {
        throw new Error("tickFormatterが取得できませんでした")
      }

      // ティックは1月のみ
      expect(ticks).toEqual([toMs("2024-01-01"), toMs("2025-01-01")])

      // 月足は常にyyyy/mm形式
      expect(tickFormatter(toMs("2024-01-01"))).toBe("2024/01")
      expect(tickFormatter(toMs("2025-01-01"))).toBe("2025/01")
    })

    it("月足の場合、1月以外の月は全てyyyy/mm形式で表示される", async () => {
      const useSWR = await import("swr")
      const monthlyData: PriceHistoryResponse = {
        symbol: "7203",
        interval: "monthly",
        data: [{ date: "2024-01-01", open: 3000, high: 3050, low: 2980, close: 3020, volume: 20000000 }],
      }

      vi.mocked(useSWR.default).mockReturnValue({
        data: monthlyData,
        isLoading: false,
        error: null,
        isValidating: false,
        mutate: vi.fn(),
      })

      render(<PriceChart symbol="7203" securityType="STOCK" />)

      const buttonMonthly = screen.getByText("月足")
      await userEvent.setup().click(buttonMonthly)

      const { ticks, tickFormatter } = getCapturedXAxisProps()
      if (!tickFormatter) {
        throw new Error("tickFormatterが取得できませんでした")
      }

      // 1月のみティック
      expect(ticks).toEqual([toMs("2024-01-01")])
      expect(tickFormatter(toMs("2024-01-01"))).toBe("2024/01")
    })

    it("エッジケース: 年変わり後の最初のデータが1月以外（2024/12 → 2025/02）", async () => {
      const useSWR = await import("swr")
      const dailyData: PriceHistoryResponse = {
        symbol: "7203",
        interval: "daily",
        data: [
          { date: "2024-12-28", open: 3000, high: 3050, low: 2980, close: 3020, volume: 1000000 },
          { date: "2025-02-03", open: 3020, high: 3080, low: 3010, close: 3060, volume: 1200000 },
        ],
      }

      vi.mocked(useSWR.default).mockReturnValue({
        data: dailyData,
        isLoading: false,
        error: null,
        isValidating: false,
        mutate: vi.fn(),
      })

      render(<PriceChart symbol="7203" securityType="STOCK" />)

      const { ticks, tickFormatter } = getCapturedXAxisProps()
      if (!tickFormatter) {
        throw new Error("tickFormatterが取得できませんでした")
      }

      expect(ticks).toEqual([toMs("2024-12-28"), toMs("2025-02-03")])

      // 最初
      expect(tickFormatter(toMs("2024-12-28"))).toBe("2024/12")
      // 年変わりの2月
      expect(tickFormatter(toMs("2025-02-03"))).toBe("2025/02")
    })
  })
})
