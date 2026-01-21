import { type ReactNode, useEffect } from "react"
import { useLocation, useNavigate } from "react-router"
import { getCurrentUser } from "@/lib/api/client"
import { useAuthStore } from "@/lib/stores/auth-store"

interface AuthProviderProps {
  children: ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const navigate = useNavigate()
  const location = useLocation()
  const { setUser, setLoading, isLoading, isAuthenticated } = useAuthStore()

  useEffect(() => {
    const checkAuth = async () => {
      try {
        const user = await getCurrentUser()
        setUser(user)
      } catch {
        setUser(null)
        if (location.pathname !== "/login") {
          navigate("/login")
        }
      } finally {
        setLoading(false)
      }
    }

    checkAuth()
  }, [location.pathname, navigate, setUser, setLoading])

  useEffect(() => {
    if (!isLoading && !isAuthenticated && location.pathname !== "/login") {
      navigate("/login")
    }
  }, [isLoading, isAuthenticated, location.pathname, navigate])

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-4">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          <p className="text-muted-foreground">Loading...</p>
        </div>
      </div>
    )
  }

  return <>{children}</>
}
