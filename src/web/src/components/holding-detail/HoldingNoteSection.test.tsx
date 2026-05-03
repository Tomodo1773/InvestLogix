import { render, screen } from "@testing-library/react"
import { userEvent } from "@testing-library/user-event"
import { describe, expect, it, vi } from "vitest"
import { HoldingNoteSection } from "./HoldingNoteSection"

vi.mock("@/lib/api/client", () => ({
  updateHoldingNote: vi.fn().mockResolvedValue({}),
}))

import { updateHoldingNote } from "@/lib/api/client"

describe("HoldingNoteSection", () => {
  it("既存のメモを表示する", () => {
    render(<HoldingNoteSection symbol="AAPL" note="AI戦略に期待" isLoading={false} onSaved={() => {}} />)
    expect(screen.getByText("AI戦略に期待")).toBeInTheDocument()
  })

  it("メモが未登録の場合はプレースホルダーを表示する", () => {
    render(<HoldingNoteSection symbol="AAPL" note={null} isLoading={false} onSaved={() => {}} />)
    expect(screen.getByText("メモは未登録です")).toBeInTheDocument()
  })

  it("編集ボタンを押すとtextareaが表示される", async () => {
    const user = userEvent.setup()
    render(<HoldingNoteSection symbol="AAPL" note="既存メモ" isLoading={false} onSaved={() => {}} />)

    await user.click(screen.getByRole("button", { name: /編集/ }))
    expect(screen.getByRole("textbox")).toHaveValue("既存メモ")
  })

  it("保存ボタンでupdateHoldingNoteが呼ばれonSavedがコールされる", async () => {
    const user = userEvent.setup()
    const onSaved = vi.fn()
    render(<HoldingNoteSection symbol="AAPL" note={null} isLoading={false} onSaved={onSaved} />)

    await user.click(screen.getByRole("button", { name: /編集/ }))
    await user.type(screen.getByRole("textbox"), "新しいメモ")
    await user.click(screen.getByRole("button", { name: /保存/ }))

    expect(updateHoldingNote).toHaveBeenCalledWith("AAPL", "新しいメモ")
    expect(onSaved).toHaveBeenCalled()
  })
})
