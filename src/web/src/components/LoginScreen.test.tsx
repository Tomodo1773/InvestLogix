import { render, screen } from "@testing-library/react"
import { userEvent } from "@testing-library/user-event"
import { describe, expect, it, vi } from "vitest"
import { LoginScreen } from "./LoginScreen"

vi.mock("@/lib/auth", () => ({
  startAccessLogin: vi.fn(),
  accessLogout: vi.fn(),
}))

import { accessLogout, startAccessLogin } from "@/lib/auth"

describe("LoginScreen", () => {
  it("ログインボタンでAccessのログインを開始する", async () => {
    const user = userEvent.setup()
    render(<LoginScreen />)

    await user.click(screen.getByRole("button", { name: "Cloudflare Accessでログイン" }))
    expect(startAccessLogin).toHaveBeenCalled()
  })

  it("ログアウトボタンでAccessのセッションを破棄する", async () => {
    const user = userEvent.setup()
    render(<LoginScreen />)

    await user.click(screen.getByRole("button", { name: "ログアウト" }))
    expect(accessLogout).toHaveBeenCalled()
  })
})
