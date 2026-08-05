/**
 * バックエンドAPIへのリバースプロキシ。
 *
 * ブラウザからは常に同一オリジンへのリクエストになるため、API側でCORSを設定する必要がなく、
 * 認証Cookieもファーストパーティ（SameSite=Lax）で扱える。
 * 転送先はVercelの環境変数 API_ORIGIN から読む（リポジトリにバックエンドのURLを残さないため）。
 */
export const config = { runtime: "edge" }

/** ボディを持てないメソッド。fetchにbodyを渡すとTypeErrorになる */
const BODYLESS_METHODS = new Set(["GET", "HEAD"])

/**
 * 転送するとレスポンスが壊れるリクエストヘッダ。
 * accept-encodingを落とすのは、圧縮の有無をランタイムに一任して
 * 「本文はデコード済みなのにcontent-encodingが残る」状態を避けるため。
 */
const STRIPPED_REQUEST_HEADERS = ["host", "connection", "content-length", "accept-encoding"]

/** 本文を再構築するため、長さ・圧縮・転送方式を示すヘッダは引き継がない */
const STRIPPED_RESPONSE_HEADERS = ["content-encoding", "content-length", "transfer-encoding"]

export default async function handler(request: Request): Promise<Response> {
  const apiOrigin = process.env.API_ORIGIN
  if (!apiOrigin) {
    return Response.json({ detail: "API_ORIGIN が設定されていません" }, { status: 500 })
  }

  const url = new URL(request.url)
  const requestHeaders = new Headers(request.headers)
  for (const name of STRIPPED_REQUEST_HEADERS) {
    requestHeaders.delete(name)
  }

  const upstream = await fetch(`${apiOrigin}${url.pathname}${url.search}`, {
    method: request.method,
    headers: requestHeaders,
    body: BODYLESS_METHODS.has(request.method) ? undefined : await request.arrayBuffer(),
    redirect: "manual",
  })

  const responseHeaders = new Headers(upstream.headers)
  for (const name of STRIPPED_RESPONSE_HEADERS) {
    responseHeaders.delete(name)
  }

  // FastAPIの末尾スラッシュ補正などが返す絶対URLはバックエンドのオリジンを含む。
  // そのまま返すとブラウザがバックエンドへ直接リダイレクトしてしまうので相対パスに直す。
  const location = responseHeaders.get("location")
  if (location?.startsWith(apiOrigin)) {
    responseHeaders.set("location", location.slice(apiOrigin.length) || "/")
  }

  return new Response(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: responseHeaders,
  })
}
