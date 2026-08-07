import { beforeEach, describe, expect, it } from "vitest"
import { useAuthStore } from "./auth-store"

const mockUser = {
  user_id: 1,
  username: "testuser",
  email: "test@example.com",
  created_at: "2024-01-01T00:00:00Z",
  line_user_id: null,
  is_admin: false,
}

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
    useAuthStore.getState().setUser(mockUser)

    const state = useAuthStore.getState()
    expect(state.user).toEqual(mockUser)
    expect(state.isAuthenticated).toBe(true)
  })

  it("setUser(null)でisAuthenticatedがfalseに戻ること", () => {
    useAuthStore.getState().setUser(mockUser)
    expect(useAuthStore.getState().isAuthenticated).toBe(true)

    useAuthStore.getState().setUser(null)

    const state = useAuthStore.getState()
    expect(state.user).toBeNull()
    expect(state.isAuthenticated).toBe(false)
  })
})
