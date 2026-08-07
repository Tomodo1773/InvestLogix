import { LogOut } from "lucide-react"
import { type ReactNode, useState } from "react"
import { Button } from "@/components/ui/button"
import { logout as logoutApi } from "@/lib/api/client"
import { useAuthStore } from "@/lib/stores/auth-store"
import { MobileNav } from "./mobile-nav"
import { Sidebar } from "./sidebar"

interface AppLayoutProps {
  children: ReactNode
}

export function AppLayout({ children }: AppLayoutProps) {
  const { user, logout } = useAuthStore()
  // 遷移は必ず起きるので解除は不要。連打防止と「処理中」の表示のためだけに持つ
  const [isLoggingOut, setIsLoggingOut] = useState(false)

  const handleLogout = async () => {
    setIsLoggingOut(true)
    try {
      await logoutApi()
    } catch {
      // サーバー側のCookie削除に失敗・タイムアウトしても、クライアント状態のリセットと遷移は行う
      // （APIが落ちていてもUIが固まらないようにする）
    }
    logout()
    window.location.href = "/login"
  }

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
              <Button variant="ghost" size="icon" onClick={handleLogout} disabled={isLoggingOut}>
                <LogOut className={`h-4 w-4 ${isLoggingOut ? "animate-spin" : ""}`} />
              </Button>
            </div>
          </div>
        </header>
        <main className="flex-1 overflow-auto bg-muted/40">{children}</main>
      </div>
    </div>
  )
}
