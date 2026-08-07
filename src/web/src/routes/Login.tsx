import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { startAccessLogin } from "@/lib/auth"

/**
 * ログイン画面
 *
 * 認証はCloudflare Accessが行うため、ここには入力欄が無い。通常はAccessが手前で
 * 認証するのでこの画面には来ず、セッション切れやアカウント未登録のときだけ表示される。
 */
export default function Login() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md shadow-lg">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center">
            <img src="/android-chrome-192x192.png" alt="InvestLogix" className="h-16 w-16 rounded-lg" />
          </div>
          <CardTitle className="text-2xl font-bold text-foreground">InvestLogix</CardTitle>
          <p className="text-muted-foreground">Portfolio Manager</p>
        </CardHeader>
        <CardContent className="space-y-4">
          <Button type="button" className="w-full" onClick={startAccessLogin}>
            Cloudflare Accessでログイン
          </Button>
          <p className="text-center text-sm text-muted-foreground">
            ログインしても表示が変わらない場合は、そのアカウントがInvestLogixに登録されていません。
          </p>
        </CardContent>
      </Card>
    </main>
  )
}
