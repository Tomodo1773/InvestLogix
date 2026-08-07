/**
 * Cloudflare Access のログイン・ログアウト
 *
 * 認証セッションはAccessが保持するため、アプリ側にはトークンもCookie操作も無い。
 * どちらもSPA内の遷移ではなくフルリロードで行う必要がある。Accessの認証はCloudflareの
 * エッジでリダイレクトとして処理されるので、fetchやreact-routerでは完結しない。
 */

/** Cloudflare Access がセッション破棄を受け付けるエンドポイント */
const ACCESS_LOGOUT_PATH = "/cdn-cgi/access/logout"

/**
 * Accessのログインを開始する
 * アプリのトップへフルリロードすると、Accessが未認証を検知してIdPへ誘導し、認証後に戻す
 */
export function startAccessLogin(): void {
  window.location.href = "/"
}

/** Accessのセッションを破棄する。破棄後はAccessのログアウト画面が表示される */
export function accessLogout(): void {
  window.location.href = ACCESS_LOGOUT_PATH
}
