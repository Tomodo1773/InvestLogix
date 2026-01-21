import { AuthProvider } from "@/components/AuthProvider"
import { Dashboard } from "@/components/dashboard/dashboard"
import { AppLayout } from "@/components/layout/app-layout"
import { useAuthStore } from "@/lib/stores/auth-store"

function DashboardContent() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)

  if (!isAuthenticated) {
    return null
  }

  return (
    <AppLayout>
      <Dashboard />
    </AppLayout>
  )
}

export default function Home() {
  return (
    <AuthProvider>
      <DashboardContent />
    </AuthProvider>
  )
}
