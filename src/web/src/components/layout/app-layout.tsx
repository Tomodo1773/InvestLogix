import { LogOut } from "lucide-react"
import type { ReactNode } from "react"
import { Button } from "@/components/ui/button"
import { accessLogout } from "@/lib/auth"
import { useCurrentUser } from "@/lib/hooks/use-current-user"
import { MobileNav } from "./mobile-nav"
import { Sidebar } from "./sidebar"

interface AppLayoutProps {
  children: ReactNode
}

export function AppLayout({ children }: AppLayoutProps) {
  const { data: user } = useCurrentUser()

  return (
    <div className="flex h-screen">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="border-b bg-card">
          <div className="flex h-16 items-center justify-between px-4">
            <div className="flex items-center gap-3">
              <MobileNav />
              <div className="flex items-center gap-3 md:hidden">
                <img src="/apple-touch-icon.png" alt="InvestLogix" className="h-10 w-10 rounded-lg" />
                <div>
                  <h1 className="text-lg font-bold text-foreground">InvestLogix</h1>
                  <p className="text-xs text-muted-foreground">Portfolio Manager</p>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-3">
              {user && <span className="text-sm text-muted-foreground">{user.username}</span>}
              <Button variant="ghost" size="icon" onClick={accessLogout} aria-label="ログアウト">
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
