import { create } from "zustand"
import type { User } from "@/lib/api/types"

/**
 * 認証済みユーザーの状態
 *
 * ログイン・ログアウトはCloudflare Accessがフルリロードを伴って行うため、
 * ストアは「今のユーザーが誰か」を保持するだけで、状態を破棄する操作は持たない。
 */
interface AuthState {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  setUser: (user: User | null) => void
  setLoading: (loading: boolean) => void
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: true,
  setUser: (user) => set({ user, isAuthenticated: !!user }),
  setLoading: (isLoading) => set({ isLoading }),
}))
