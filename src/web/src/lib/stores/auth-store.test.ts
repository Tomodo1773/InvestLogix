import { beforeEach, describe, expect, it } from "vitest"
import { useAuthStore } from "./auth-store"

describe("useAuthStore", () => {
  beforeEach(() => {
    // テスト間で状態をリセット
    useAuthStore.setState({
      user: null,
      isAuthenticated: false,
      isLoading: true,
    })
  })

  it("setUserでユーザーを設定するとisAuthenticatedがtrueになること", () => {
    const mockUser = {
      user_id: 1,
      username: "testuser",
      email: "test@example.com",
      created_at: "2024-01-01T00:00:00Z",
      line_user_id: null,
      is_admin: false,
    }

    useAuthStore.getState().setUser(mockUser)

    const state = useAuthStore.getState()
    expect(state.user).toEqual(mockUser)
    expect(state.isAuthenticated).toBe(true)
  })

  it("logoutで状態がリセットされること", () => {
    const mockUser = {
      user_id: 1,
      username: "testuser",
      email: "test@example.com",
      created_at: "2024-01-01T00:00:00Z",
      line_user_id: null,
      is_admin: false,
    }

    // ユーザーを設定
    useAuthStore.getState().setUser(mockUser)
    expect(useAuthStore.getState().isAuthenticated).toBe(true)

    // ログアウト
    useAuthStore.getState().logout()

    const state = useAuthStore.getState()
    expect(state.user).toBeNull()
    expect(state.isAuthenticated).toBe(false)
  })
})
