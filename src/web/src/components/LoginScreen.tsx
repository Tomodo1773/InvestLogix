import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { accessLogout, startAccessLogin } from "@/lib/auth"

/**
 * ログイン画面
 *
 * 認証はCloudflare Accessが行うため入力欄は無い。Accessが手前で認証するので
 * 通常この画面には来ず、セッション切れかアカウント未登録のときだけ表示される。
 *
 * アカウント未登録のときはログインし直しても状況が変わらないため、別のアカウントへ
 * 切り替えられるようログアウトも置く。この画面はAppLayoutの代わりに描画されるので、
 * ヘッダーのログアウトには手が届かない。
 */
export function LoginScreen() {
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
          <Button type="button" variant="outline" className="w-full" onClick={accessLogout}>
            ログアウト
          </Button>
          <p className="text-center text-sm text-muted-foreground">
            ログインしても表示が変わらない場合は、そのアカウントがInvestLogixに登録されていません。
            ログアウトして別のアカウントでログインしてください。
          </p>
        </CardContent>
      </Card>
    </main>
  )
}
