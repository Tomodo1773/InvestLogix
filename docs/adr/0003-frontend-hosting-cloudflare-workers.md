# ADR 0003: フロントエンドのホスティングを Cloudflare Workers に移す

- ステータス: Accepted
- 日付: 2026-08-06
- 関連: PR #431

## 背景

フロントエンド（`src/web`、React + Vite の SPA）は Vercel、バックエンド（`src/api`、FastAPI）は Google Cloud Run にデプロイしていた。この構成には2つの問題があった。

### 1. 認証 Cookie がサードパーティ Cookie になっていた

フロントが `*.vercel.app`、API が `*.run.app` で eTLD+1 が異なるため、`/api/v1/token` が発行する認証 Cookie は構造的にサードパーティ Cookie だった。これを成立させるために `src/api/stock/routes/auth.py` で `samesite="none"` を強制し、`src/api/stock/app.py` で CORS を開けていた（`allow_origin_regex` に Vercel の組織名がハードコードされている状態）。

Safari の ITP や Brave はサードパーティ Cookie をデフォルトで遮断するため、Chrome 以外ではログインが通らない状態にあった。これは設定の調整では解決せず、**フロントと API を同一オリジンに置く以外に根本解決がない**。

### 2. Vercel を使う理由がなかった

`src/web/vercel.json` の中身は SPA フォールバックの rewrite 1行だけで、SSR / ISR / Edge Functions / Image Optimization はいずれも未使用だった。Vercel 固有の依存も `@vercel/analytics` のみ。実態は「`dist/` を配って 404 を `index.html` に返す静的ホスティング」であり、Vite の SPA である以上その役割は他でも代替できる。

## 決定

**Cloudflare Workers（Static Assets）へ移行し、`/api/*` を Worker から Cloud Run へプロキシして同一オリジンにする。**

- `src/web/worker/index.ts` が `/api/*` を受け、`env.API_ORIGIN` へ転送する
- `src/web/wrangler.jsonc` の `not_found_handling: "single-page-application"` が従来の `vercel.json` の rewrite を置き換える
- `run_worker_first: ["/api/*"]` により、`/api/*` 以外は Worker を起動せずアセット配信される（Worker のリクエスト課金対象にならない）
- バックエンドのオリジンは `wrangler secret put API_ORIGIN` で Cloudflare 側に置き、設定ファイルには書かない
- カスタムドメインも `wrangler.jsonc` の `routes` に書かず、ダッシュボードで attach する

あわせて `VITE_API_URL` を廃止し、フロントは常に相対パスで API を叩く。開発時は Vite の dev proxy が Worker と同じ役割を担うため、dev と prod で経路の形が揃う。

### なぜ Vercel のプロキシではないのか

Vercel の `rewrites` でも同一オリジン化はできる。採用しなかったのは、`vercel.json` が静的 JSON のためバックエンドの URL を公開リポジトリにコミットするしかない点にある。

Worker は設定ファイルではなく**コード**なので、オリジンを Secret から読める（`env.API_ORIGIN`）。この違いが決定的だった。

副次的な効果として、これまで `VITE_API_URL` はビルド時に JS バンドルへ焼き込まれ、DevTools を開けば誰にでも見える状態だったが、相対パス化によりブラウザからも Cloud Run の URL が見えなくなる。

## 代替案

### Firebase Hosting

`rewrites` で Cloud Run サービスを直接指定でき、同一オリジン化を無料枠で実現できる唯一の Google Cloud 側の選択肢。インフラを Google Cloud に集約できる利点もあった。

採用しなかった理由は、この移行を学習目的も兼ねて行っており、宣言的な rewrite 設定より Workers ランタイムを触るほうが得るものが大きいと判断したため。加えて Secret でオリジンを隠す要件を満たすのは Worker 側だった。

### Cloud Storage + Cloud CDN + External Load Balancer

URL map と serverless NEG で完全な同一オリジン化ができ、`infra/*.tf` で全て記述できるため IaC との相性は最良。

採用しなかった理由はコスト。Load Balancer は転送ルールが常時課金となり、月 $20 前後が固定で乗る。「運用コストと手段は 1 人規模に合わせる」という本プロジェクトの方針に照らして見合わない。

### Vercel を継続し、rewrites でプロキシする

上述のとおり、バックエンドの URL を公開リポジトリにコミットせざるを得ないため却下した。

## 影響

### 良い面

- `samesite="none"` と CORS ミドルウェアを撤去できる。Safari / Brave でログインが通るようになる
- バックエンドの URL がリポジトリにもクライアントバンドルにも現れなくなる
- dev（Vite dev proxy）と prod（Worker proxy）で経路の形が揃い、環境変数が1つ減る
- `pnpm-lock.yaml` 以外の依存追加は `wrangler` のみで、ロックインはほぼない

### 注意する面

- **`compatibility_date` は同梱 workerd がサポートする上限日以下でなければならない。** 超えると `wrangler dev` が起動しない。`minimumReleaseAge: 10080` により wrangler は7日以上前のバージョンが入るため、上限は「今日」より前になる。制約は一方向（wrangler を上げれば上限が上がる）なので、依存更新に追随して上げる必要はない
- **`wrangler` をクールダウン除外リストに入れても効かない。** wrangler は `workerd` / `miniflare` を同日リリースの完全固定で要求するため、`wrangler` 単体を除外しても依存側で止まる。`vite` に対して `rolldown` / `@rolldown/*` も併記しているのと同じ構図。`workerd` は Worker コードを実行するネイティブバイナリであり、クールダウンを効かせておく価値が最も高い対象なので除外しない方針とした
- **`worker/` と `src/` は tsconfig を分ける必要がある。** `Request` / `Response` / `fetch` の型が Workers ランタイムと DOM で衝突する。`pnpm typecheck` は両方を検査する
- **`worker-configuration.d.ts` はコミットしない。** 14000行超あるうえ、`wrangler types` がローカルの `.dev.vars` の変数名を読み取って `Env` に含めるため、マシン間で内容が一致しない。`pnpm typecheck` の先頭で毎回生成する（`prepare` は pnpm が "Already up to date" のときスキップするため使えなかった）
- **Worker のプロキシはリダイレクトを追う必要がある。** FastAPI は末尾スラッシュ不一致で 307 を返し、その `Location` は絶対 URL（Host がバックエンドのもの）になる。ブラウザに渡すとクロスサイト遷移になって Cookie が送られず、かつバックエンドの URL が露出する。`redirect: "follow"` を明示すること（Workers の受信 Request は `redirect` が `manual` なので暗黙に引き継がれる）
- **さらに、リダイレクトを追うにはボディをバッファで渡す必要がある。** 受信 Request のボディはストリームなので、リダイレクトで再送が必要になると `TypeError: A request with a one-time-use body ... encountered a redirect requiring the body to be retransmitted` になる。GET は影響しないため気づきにくく、ログインや CSV インポートのような POST だけが 500 になる
- **`API_ORIGIN` は `https://` で登録する。** `http://` だと Cloud Run が HTTPS へリダイレクトし、上記のボディ再送エラーを踏む。GET は透過的に追従して成功するため原因が分かりにくい
- **`API_ORIGIN` に同一ゾーン内のカスタムドメインを指定してはいけない。** Worker から自分と同じゾーンのホストへ `fetch` するとリダイレクトループになる（Cloudflare の既知の制約。回避策として案内される Service Bindings は Worker 間専用で、転送先が Cloud Run の本構成では使えない）。Worker の転送先は Cloud Run の `*.run.app` を直接指定する。API のカスタムドメインは Swagger UI や手動確認といった「人間が直接触る入口」として引き続き有効
- Cookie の `samesite` 変更と CORS 撤去は、DNS を Vercel に戻すロールバック手段を残すため、切り替え検証が済んでから別コミットで行った（PR #435）。**これを当てた時点で Vercel へのロールバックはできなくなる**（`samesite=lax` かつ CORS なしの API は `*.vercel.app` からのリクエストを通せない）。以降のロールバック手段は Worker の再デプロイのみ
- API はどのオリジンからも CORS ヘッダーを返さなくなった。将来フロントを別オリジンに置く構成に戻すなら CORS ミドルウェアの再導入が必要になる
- 同 PR で Vercel の残骸（`vercel.json`、Vercel の `projectId` / `orgId` を含む `project.json`、`@vercel/analytics`）も撤去した。アクセス解析の代替は入れていない
