import type { ReactNode } from "react"
import { AuthProvider } from "@/components/AuthProvider"
import { AppLayout } from "@/components/layout/app-layout"

interface AuthenticatedLayoutProps {
  children: ReactNode
}

/** 全ページ共通の枠。ユーザーの解決（AuthProvider）と画面レイアウト（AppLayout）をまとめる */
export function AuthenticatedLayout({ children }: AuthenticatedLayoutProps) {
  return (
    <AuthProvider>
      <AppLayout>{children}</AppLayout>
    </AuthProvider>
  )
}
