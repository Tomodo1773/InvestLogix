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
vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="recharts-container">{children}</div>
  ),
  LineChart: ({ children }: { children: React.ReactNode }) => <div data-testid="line-chart">{children}</div>,
  Line: () => <div data-testid="line" />,
  XAxis: () => <div data-testid="x-axis" />,
  YAxis: () => <div data-testid="y-axis" />,
  CartesianGrid: () => <div data-testid="cartesian-grid" />,
  Tooltip: () => <div data-testid="tooltip" />,
  ReferenceLine: ({ label, x }: { label?: { value: string }; x?: string }) => (
    <div data-testid={`reference-line-${x}`} data-label={label?.value} />
  ),
}))

const mockPriceData: PriceHistoryResponse = {
  symbol: "7203",
  period: "1Y",
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

describe("PriceChart", () => {
  it("投資信託の場合は非表示になること", () => {
    const { container } = render(<PriceChart symbol="12345" securityType="FUND" />)
    expect(container.firstChild).toBeNull()
  })

  it("期間切り替えボタンが表示されること", async () => {
    const useSWR = await import("swr")
    vi.mocked(useSWR.default).mockReturnValue({
      data: mockPriceData,
      isLoading: false,
      error: null,
      isValidating: false,
      mutate: vi.fn(),
    })

    render(<PriceChart symbol="7203" securityType="STOCK" />)

    // 期間ボタンが表示されること
    expect(screen.getByText("1M")).toBeInTheDocument()
    expect(screen.getByText("3M")).toBeInTheDocument()
    expect(screen.getByText("6M")).toBeInTheDocument()
    expect(screen.getByText("1Y")).toBeInTheDocument()
    expect(screen.getByText("3Y")).toBeInTheDocument()
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

  it("ローディング状態でスピナーが表示されること", async () => {
    const useSWR = await import("swr")
    vi.mocked(useSWR.default).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
      isValidating: false,
      mutate: vi.fn(),
    })

    render(<PriceChart symbol="7203" securityType="STOCK" />)

    // スピナーが表示されていることを確認
    const spinner = document.querySelector(".animate-spin")
    expect(spinner).toBeInTheDocument()
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
      data: { symbol: "7203", period: "1Y", interval: "daily", data: [] },
      isLoading: false,
      error: null,
      isValidating: false,
      mutate: vi.fn(),
    })

    render(<PriceChart symbol="7203" securityType="STOCK" />)

    expect(screen.getByText("データがありません")).toBeInTheDocument()
  })

  it("期間ボタンをクリックすると選択状態が変わること", async () => {
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

    const button3M = screen.getByText("3M")

    // 初期状態では1Yが選択されている
    const button1Y = screen.getByText("1Y")
    expect(button1Y).toHaveClass("bg-primary")

    // 3Mボタンをクリック
    await user.click(button3M)

    // 3Mが選択状態になる
    expect(button3M).toHaveClass("bg-primary")
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

  it("データがある場合にグラフが表示されること", async () => {
    const useSWR = await import("swr")
    vi.mocked(useSWR.default).mockReturnValue({
      data: mockPriceData,
      isLoading: false,
      error: null,
      isValidating: false,
      mutate: vi.fn(),
    })

    render(<PriceChart symbol="7203" securityType="STOCK" />)

    // Rechartsコンポーネントが表示されていることを確認
    expect(screen.getByTestId("recharts-container")).toBeInTheDocument()
    expect(screen.getByTestId("line-chart")).toBeInTheDocument()
  })

  it("年の変わり目に参照線が表示されること", async () => {
    const useSWR = await import("swr")
    const multiYearData: PriceHistoryResponse = {
      symbol: "7203",
      period: "3Y",
      interval: "daily",
      data: [
        { date: "2023-12-28", open: 2800, high: 2850, low: 2780, close: 2820, volume: 900000 },
        { date: "2023-12-29", open: 2820, high: 2880, low: 2810, close: 2850, volume: 950000 },
        { date: "2024-01-04", open: 2850, high: 2900, low: 2840, close: 2880, volume: 1000000 },
        { date: "2024-01-05", open: 2880, high: 2920, low: 2870, close: 2900, volume: 1050000 },
        { date: "2024-12-27", open: 2950, high: 3000, low: 2940, close: 2980, volume: 1100000 },
        { date: "2024-12-30", open: 2980, high: 3020, low: 2970, close: 3000, volume: 1150000 },
        { date: "2025-01-06", open: 3000, high: 3050, low: 2990, close: 3020, volume: 1200000 },
        { date: "2025-01-07", open: 3020, high: 3080, low: 3010, close: 3060, volume: 1250000 },
      ],
    }

    vi.mocked(useSWR.default).mockReturnValue({
      data: multiYearData,
      isLoading: false,
      error: null,
      isValidating: false,
      mutate: vi.fn(),
    })

    render(<PriceChart symbol="7203" securityType="STOCK" />)

    // 2024年の変わり目の参照線が存在すること
    const referenceLine2024 = screen.getByTestId("reference-line-2024-01-04")
    expect(referenceLine2024).toBeInTheDocument()
    expect(referenceLine2024).toHaveAttribute("data-label", "2024")

    // 2025年の変わり目の参照線が存在すること
    const referenceLine2025 = screen.getByTestId("reference-line-2025-01-06")
    expect(referenceLine2025).toBeInTheDocument()
    expect(referenceLine2025).toHaveAttribute("data-label", "2025")
  })

  it("年をまたがないデータでは年の参照線が表示されないこと", async () => {
    const useSWR = await import("swr")
    vi.mocked(useSWR.default).mockReturnValue({
      data: mockPriceData, // 2025年のデータのみ
      isLoading: false,
      error: null,
      isValidating: false,
      mutate: vi.fn(),
    })

    const { container } = render(<PriceChart symbol="7203" securityType="STOCK" />)

    // 年の参照線が存在しないこと（買付日の参照線のみ）
    const referenceLines = container.querySelectorAll('[data-testid^="reference-line-"]')
    const yearReferenceLines = Array.from(referenceLines).filter((el) => el.getAttribute("data-label"))
    expect(yearReferenceLines).toHaveLength(0)
  })
})
