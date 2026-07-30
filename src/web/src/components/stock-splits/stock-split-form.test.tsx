import { render, screen } from "@testing-library/react"
import { userEvent } from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { StockSplitForm } from "./stock-split-form"

vi.mock("@/lib/api/client", () => ({
  createStockSplit: vi.fn(),
}))

import { createStockSplit } from "@/lib/api/client"

const mockedCreateStockSplit = vi.mocked(createStockSplit)

/** 銘柄コードと分割基準日を埋めて、あとは株数だけを操作できる状態にする */
async function fillRequiredFields(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText("銘柄コード"), "7203")
  await user.type(screen.getByLabelText("分割基準日"), "2024-06-01")
}

describe("StockSplitForm", () => {
  beforeEach(() => {
    mockedCreateStockSplit.mockReset()
    mockedCreateStockSplit.mockResolvedValue({
      split_id: 1,
      user_id: 1,
      symbol: "7203",
      split_date: "2024-06-01T00:00:00+09:00",
      split_ratio: 2,
      created_at: "2024-06-02T10:00:00+09:00",
      stock_name: "トヨタ自動車",
    })
  })

  it("入力した株数から分割比率のプレビューを表示する", async () => {
    const user = userEvent.setup()
    render(<StockSplitForm onCreated={() => {}} onCancel={() => {}} />)

    // 初期値は 1株 → 2株
    expect(screen.getByText("登録内容: 2:1 分割")).toBeInTheDocument()

    await user.clear(screen.getByLabelText("分割後株数"))
    await user.type(screen.getByLabelText("分割後株数"), "4")
    expect(screen.getByText("登録内容: 4:1 分割")).toBeInTheDocument()
  })

  it("併合の株数を入力すると併合として表示する", async () => {
    const user = userEvent.setup()
    render(<StockSplitForm onCreated={() => {}} onCancel={() => {}} />)

    await user.clear(screen.getByLabelText("分割前株数"))
    await user.type(screen.getByLabelText("分割前株数"), "2")
    await user.clear(screen.getByLabelText("分割後株数"))
    await user.type(screen.getByLabelText("分割後株数"), "1")

    expect(screen.getByText("登録内容: 1:2 併合")).toBeInTheDocument()
  })

  it("必須項目が未入力のときは登録ボタンが無効になる", () => {
    render(<StockSplitForm onCreated={() => {}} onCancel={() => {}} />)

    expect(screen.getByRole("button", { name: "登録" })).toBeDisabled()
  })

  it("分割前後の株数が同じときは登録ボタンが無効になり理由を表示する", async () => {
    const user = userEvent.setup()
    render(<StockSplitForm onCreated={() => {}} onCancel={() => {}} />)

    await fillRequiredFields(user)
    await user.clear(screen.getByLabelText("分割後株数"))
    await user.type(screen.getByLabelText("分割後株数"), "1")

    expect(screen.getByText("分割前と分割後で異なる株数を入力してください")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "登録" })).toBeDisabled()
  })

  it("登録するとAPIに分割比率が渡りonCreatedが呼ばれる", async () => {
    const user = userEvent.setup()
    const onCreated = vi.fn()
    render(<StockSplitForm onCreated={onCreated} onCancel={() => {}} />)

    await fillRequiredFields(user)
    await user.clear(screen.getByLabelText("分割後株数"))
    await user.type(screen.getByLabelText("分割後株数"), "4")
    await user.click(screen.getByRole("button", { name: "登録" }))

    expect(mockedCreateStockSplit).toHaveBeenCalledWith({
      symbol: "7203",
      split_date: "2024-06-01",
      split_ratio: 4,
    })
    expect(onCreated).toHaveBeenCalled()
  })

  it("APIがエラーを返した場合はエラーメッセージを表示しonCreatedを呼ばない", async () => {
    const user = userEvent.setup()
    const onCreated = vi.fn()
    mockedCreateStockSplit.mockRejectedValue(
      new Error("同じ銘柄・同じ分割基準日の株式分割がすでに登録されています")
    )
    render(<StockSplitForm onCreated={onCreated} onCancel={() => {}} />)

    await fillRequiredFields(user)
    await user.click(screen.getByRole("button", { name: "登録" }))

    expect(
      await screen.findByText("同じ銘柄・同じ分割基準日の株式分割がすでに登録されています")
    ).toBeInTheDocument()
    expect(onCreated).not.toHaveBeenCalled()
  })

  it("キャンセルするとonCancelが呼ばれる", async () => {
    const user = userEvent.setup()
    const onCancel = vi.fn()
    render(<StockSplitForm onCreated={() => {}} onCancel={onCancel} />)

    await user.click(screen.getByRole("button", { name: "キャンセル" }))

    expect(onCancel).toHaveBeenCalled()
  })
})
