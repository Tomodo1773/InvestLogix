import useSWR from "swr"
import { getCurrentUser } from "@/lib/api/client"
import { SWR_KEYS } from "@/lib/api/keys"

/**
 * ログイン中のユーザーを取得する
 *
 * 認証状態を持つストアは置かない。誰がログインしているかはサーバーが持っていて、
 * クライアントはそれを取得してキャッシュするだけだから。SWRが同じキーの取得を
 * まとめるので、複数のコンポーネントから呼んでもリクエストは1回で済む。
 */
export function useCurrentUser() {
  return useSWR(SWR_KEYS.me, getCurrentUser)
}
