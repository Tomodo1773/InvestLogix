/**
 * フロントと同一オリジンで `/api/*` を受け、バックエンド（Cloud Run）へ転送する。
 *
 * 同一オリジンにすることが目的。フロントとAPIが別サイトだと認証Cookieが
 * サードパーティCookieになり、SameSite=None を強制されてSafari等で遮断される。
 *
 * バックエンドのURLは Secret（API_ORIGIN）から読むため、リポジトリにも
 * クライアントバンドルにも現れない。
 */
interface Env {
  /** バックエンドのオリジン。`wrangler secret put API_ORIGIN` で登録する */
  API_ORIGIN: string
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url)

    // Host は fetch が転送先URLから導出する。Cloud Run は Host でルーティングするため、
    // 元の Host を引き継いではいけない（Request構築時に Host は引き継がれない）
    const target = new URL(url.pathname + url.search, env.API_ORIGIN)

    return fetch(new Request(target, request), {
      // APIのリダイレクトはWorkerが追わずブラウザに返す。
      // Workerが追うと Location にバックエンドのURLが露出する
      redirect: "manual",
    })
  },
} satisfies ExportedHandler<Env>
