import { render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import type { MonthlySummaryItem } from "@/lib/api/types"
import { NisaLimitGauge } from "./nisa-limit-gauge"

const mockData: MonthlySummaryItem[] = [
  {
    year: 2026,
    month: 1,
    total_purchase: {
      NISAGrowth: 500_000,
      NISAAccumulation: 300_000,
    },
  },
  {
    year: 2026,
    month: 2,
    total_purchase: {
      NISAGrowth: 1_000_000,
      NISAAccumulation: 200_000,
    },
  },
  {
    year: 2025,
    month: 12,
    total_purchase: {
      NISAGrowth: 500_000,
      NISAAccumulation: 400_000,
    },
  },
]

describe("NisaLimitGauge", () => {
  it("現在年のNISA投資枠データを正しく表示すること", () => {
    // 現在年を2026年にモック
    vi.setSystemTime(new Date("2026-01-27"))

    render(<NisaLimitGauge data={mockData} isLoading={false} />)

    // タイトルの確認
    expect(screen.getByText("NISA投資枠")).toBeInTheDocument()

    // 成長投資枠のラベル
    expect(screen.getByText("成長投資枠")).toBeInTheDocument()

    // つみたて投資枠のラベル
    expect(screen.getByText("つみたて投資枠")).toBeInTheDocument()

    // 成長投資枠の金額: 500,000 + 1,000,000 = 1,500,000
    expect(screen.getByText("¥1,500,000 / ¥2,400,000")).toBeInTheDocument()

    // つみたて投資枠の金額: 300,000 + 200,000 = 500,000
    expect(screen.getByText("¥500,000 / ¥1,200,000")).toBeInTheDocument()

    vi.useRealTimers()
  })

  it("データがundefinedの場合に0円と表示されること", () => {
    render(<NisaLimitGauge data={undefined} isLoading={false} />)

    expect(screen.getByText("¥0 / ¥2,400,000")).toBeInTheDocument()
    expect(screen.getByText("¥0 / ¥1,200,000")).toBeInTheDocument()
  })

  it("データが空配列の場合に0円と表示されること", () => {
    render(<NisaLimitGauge data={[]} isLoading={false} />)

    expect(screen.getByText("¥0 / ¥2,400,000")).toBeInTheDocument()
    expect(screen.getByText("¥0 / ¥1,200,000")).toBeInTheDocument()
  })

  it("前年のデータが含まれていても現在年のみが計算されること", () => {
    vi.setSystemTime(new Date("2026-02-15"))

    render(<NisaLimitGauge data={mockData} isLoading={false} />)

    // 2025年のデータ(500,000/400,000)は含まれない
    // 2026年のデータのみ: 1,500,000 / 500,000
    expect(screen.getByText("¥1,500,000 / ¥2,400,000")).toBeInTheDocument()
    expect(screen.getByText("¥500,000 / ¥1,200,000")).toBeInTheDocument()

    vi.useRealTimers()
  })

  it("残り枠が正しく計算されること", () => {
    vi.setSystemTime(new Date("2026-01-27"))

    render(<NisaLimitGauge data={mockData} isLoading={false} />)

    // 成長投資枠の残り: 2,400,000 - 1,500,000 = 900,000
    expect(screen.getByText("残り ¥900,000")).toBeInTheDocument()

    // つみたて投資枠の残り: 1,200,000 - 500,000 = 700,000
    expect(screen.getByText("残り ¥700,000")).toBeInTheDocument()

    vi.useRealTimers()
  })

  it("パーセンテージが正しく表示されること", () => {
    vi.setSystemTime(new Date("2026-01-27"))

    render(<NisaLimitGauge data={mockData} isLoading={false} />)

    // 成長投資枠: 1,500,000 / 2,400,000 = 62.5%
    expect(screen.getByText("62.5%")).toBeInTheDocument()

    // つみたて投資枠: 500,000 / 1,200,000 = 41.666...%
    expect(screen.getByText("41.7%")).toBeInTheDocument()

    vi.useRealTimers()
  })

  it("NISAGrowthのみのデータでも正しく動作すること", () => {
    vi.setSystemTime(new Date("2026-01-27"))

    const dataWithGrowthOnly: MonthlySummaryItem[] = [
      {
        year: 2026,
        month: 1,
        total_purchase: {
          NISAGrowth: 1_000_000,
        },
      },
    ]

    render(<NisaLimitGauge data={dataWithGrowthOnly} isLoading={false} />)

    expect(screen.getByText("¥1,000,000 / ¥2,400,000")).toBeInTheDocument()
    expect(screen.getByText("¥0 / ¥1,200,000")).toBeInTheDocument()

    vi.useRealTimers()
  })

  it("NISAAccumulationのみのデータでも正しく動作すること", () => {
    vi.setSystemTime(new Date("2026-01-27"))

    const dataWithAccumulationOnly: MonthlySummaryItem[] = [
      {
        year: 2026,
        month: 1,
        total_purchase: {
          NISAAccumulation: 600_000,
        },
      },
    ]

    render(<NisaLimitGauge data={dataWithAccumulationOnly} isLoading={false} />)

    expect(screen.getByText("¥0 / ¥2,400,000")).toBeInTheDocument()
    expect(screen.getByText("¥600,000 / ¥1,200,000")).toBeInTheDocument()

    vi.useRealTimers()
  })
})
