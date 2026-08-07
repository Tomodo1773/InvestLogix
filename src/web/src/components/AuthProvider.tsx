import type { ReactNode } from "react"
import { LoginScreen } from "@/components/LoginScreen"
import { useCurrentUser } from "@/lib/hooks/use-current-user"

interface AuthProviderProps {
  children: ReactNode
}

/**
 * ログイン中のユーザーを解決してから中身を表示する
 *
 * 認証そのものはCloudflare Accessがドキュメント要求の時点で終えているため、
 * SPAが未認証のまま起動することはない。ここが確かめるのは
 * 「Accessが通した利用者がInvestLogixに登録されているか」と「セッションが生きているか」だけ。
 * 解決できないときはログイン画面を出す。画面遷移はしない（Accessの再認証はフルリロードで起きる）。
 */
export function AuthProvider({ children }: AuthProviderProps) {
  const { data: user, isLoading } = useCurrentUser()

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

  if (!user) {
    return <LoginScreen />
  }

  return <>{children}</>
}
