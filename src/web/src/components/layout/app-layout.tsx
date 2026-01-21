import { LogOut, TrendingUp } from "lucide-react"
import type { ReactNode } from "react"
import { Button } from "@/components/ui/button"
import { useAuthStore } from "@/lib/stores/auth-store"
import { MobileNav } from "./mobile-nav"
import { Sidebar } from "./sidebar"

interface AppLayoutProps {
  children: ReactNode
}

export function AppLayout({ children }: AppLayoutProps) {
  const { user, logout } = useAuthStore()

  const handleLogout = () => {
    logout()
    window.location.href = "/login"
  }

  return (
    <div className="flex h-screen">
      <Sidebar />
      <div className="flex flex-1 flex-col">
        <header className="border-b bg-card">
          <div className="flex h-16 items-center justify-between px-4">
            <div className="flex items-center gap-3">
              <MobileNav />
              <div className="flex items-center gap-3 md:hidden">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary">
                  <TrendingUp className="h-5 w-5 text-primary-foreground" />
                </div>
                <div>
                  <h1 className="text-lg font-bold text-foreground">InvestLogix</h1>
                  <p className="text-xs text-muted-foreground">Portfolio Manager</p>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-3">
              {user && <span className="text-sm text-muted-foreground">{user.username}</span>}
              <Button variant="ghost" size="icon" onClick={handleLogout}>
                <LogOut className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </header>
        <main className="flex-1 overflow-auto bg-muted/40">{children}</main>
      </div>
    </div>
  )
}
