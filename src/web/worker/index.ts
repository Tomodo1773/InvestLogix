/**
 * フロントと同一オリジンで `/api/*` を受け、バックエンド（Cloud Run）へ転送する。
 *
 * 同一オリジンにすることが目的。このドメインは Cloudflare Access で保護されており、
 * Access は認証を通したリクエストにだけ `Cf-Access-Jwt-Assertion` を付けて Worker へ渡す。
 * フロントとAPIが別サイトだと、APIリクエストがこの保護の外を通ってしまう。
 * 受け取ったヘッダーはそのまま転送し、署名の検証はバックエンドが行う。
 *
 * バックエンドのURLは Secret（API_ORIGIN）から読むため、リポジトリにも
 * クライアントバンドルにも現れない。
 */
interface Env {
  /** バックエンドのオリジン。`wrangler secret put API_ORIGIN` で登録する */
  API_ORIGIN: string
}

/** ボディを持ちえないメソッド。これ以外はバッファに読み切ってから転送する */
const BODYLESS_METHODS = new Set(["GET", "HEAD"])

export default {
  async fetch(request, env) {
    const url = new URL(request.url)
    const target = new URL(url.pathname + url.search, env.API_ORIGIN)

    // Host は転送先URLから導出させる。Cloud Run は Host でルーティングするため、
    // 元の Host（フロントのドメイン）を引き継ぐと転送先に届かない
    const headers = new Headers(request.headers)
    headers.delete("host")

    // ボディはストリームのままだと「リダイレクトで再送が必要になったとき」に
    // 例外になる（GETは影響しないが、CSVインポート等のPOSTが落ちる）。
    // 読み切ってバッファで渡すことでリダイレクトを跨げるようにする。
    // 個人利用の範囲ではアップロードサイズが小さいため全読みで問題ない
    const body = BODYLESS_METHODS.has(request.method) ? undefined : await request.arrayBuffer()

    return fetch(target, {
      method: request.method,
      headers,
      body,
      // リダイレクトはWorker側で追い、ブラウザには最終結果だけを返す。
      // ブラウザに3xxを渡すと Location が絶対URL（Host がバックエンドのもの）なので
      // クロスサイト遷移になりCookieが送られず、かつバックエンドのURLが露出する。
      // Workersの受信Requestは redirect が manual なので明示的に上書きする
      redirect: "follow",
    })
  },
} satisfies ExportedHandler<Env>
