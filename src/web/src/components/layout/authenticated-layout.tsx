import type { ReactNode } from "react"
import { AuthProvider } from "@/components/AuthProvider"
import { AppLayout } from "@/components/layout/app-layout"
import { useAuthStore } from "@/lib/stores/auth-store"

interface AuthenticatedLayoutProps {
  children: ReactNode
}

function AuthenticatedContent({ children }: AuthenticatedLayoutProps) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)

  if (!isAuthenticated) {
    return null
  }

  return <AppLayout>{children}</AppLayout>
}

export function AuthenticatedLayout({ children }: AuthenticatedLayoutProps) {
  return (
    <AuthProvider>
      <AuthenticatedContent>{children}</AuthenticatedContent>
    </AuthProvider>
  )
}
