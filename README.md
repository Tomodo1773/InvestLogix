# InvestLogix

InvestLogixは、日本株・米国株の取引/保有/配当を記録し、ポートフォリオを可視化するWebアプリケーションです。

- バックエンド: FastAPI（`src/api`）
- フロントエンド: React + Vite（`src/web`）
- DB: PostgreSQL（ローカル開発はDocker推奨）

## 主な機能

- 銘柄管理（日本株・米国株、銘柄詳細情報）
- 取引管理（購入/売却、口座種別、月次/年次サマリー）
- 保有株管理（平均取得単価・口座種別ごとの保有数量の自動計算、評価損益）
- 配当管理（配当履歴、月次集計、銘柄別集計）
- ポートフォリオ分析（資産推移、通貨/市場別の分布、銘柄別配当割合、サマリー）
- LINE通知（ポートフォリオ状況の通知）
- 認証（JWT）

## 構成

### アプリ
- フロントエンド: React（Vite）
- バックエンド: FastAPI（Python 3.13）
- 定時ジョブ: Python（`python -m` で起動）
- DB: PostgreSQL

### インフラ
- フロントエンド: Cloudflare Workers（Static Assets）
  - `/api/*` は Worker が Cloud Run へプロキシする。フロントとAPIを同一オリジンにすることで、認証Cookieがサードパーティ扱いにならずSafari等でも通る
  - バックエンドのオリジンは Worker の Secret（`API_ORIGIN`）に置くため、リポジトリにもクライアントバンドルにも現れない
- バックエンド: Google Cloud Run
  - API は Cloud Run Service
  - 定時ジョブは Cloud Run Jobs ＋ Cloud Scheduler
- DB: Supabase（マネージド PostgreSQL）
- シークレットは事前に Secret Manager に登録
- 上記の構造（env, IAM, scaling, cron 等）は OpenTofu でプロビジョニング

### デプロイと運用
- アプリのデプロイ: フロントは `web-cd.yml` による Cloudflare Workers 自動デプロイ、バックエンドは Cloud Build による Cloud Run 自動デプロイ
- インフラ構造の変更: `infra/*.tf` を編集して `tofu apply`
- シークレット値の更新: `gcloud secrets versions add`（Terraform は値を持たない）
- Cloud Run Jobs のイメージ更新: main マージ後に `scripts/update-cloud-run-jobs.sh`
- 株価データは `price_history` テーブルから読み込む。日次バッチ `recalc-holdings` が冒頭で直近2週間分を upsert する。新規環境やマイグレーション直後はテーブルが空でダッシュボードに評価額が出ないため、`gcloud run jobs execute recalc-holdings` で手動実行するか翌朝のスケジュール実行を待つ

### 依存関係の防御
サプライチェーン攻撃対策として [Socket Firewall Free](https://docs.socket.dev/docs/socket-firewall-free) を導入しています。依存関係を取得するときは `sfw` 経由で実行します。

## リポジトリ構成

```
InvestLogix/
├── src/
│   ├── api/                 # FastAPI API + 定時ジョブ
│   ├── web/                 # React + Vite SPA
│   ├── docker-compose.yaml  # ローカル開発用（DB + API）
│   └── Dockerfile           # API のコンテナイメージ
├── infra/                   # OpenTofu (Google Cloud)
├── scripts/                 # 運用スクリプト（Cloud Run Jobs 更新等）
└── samples/                 # SBI証券エクスポートサンプル
```

## クイックスタート（ローカル開発）

### 1) DB + API を起動（Docker）

```bash
cd src
docker compose up -d --build
```

- API: `http://localhost:8000`
- APIドキュメント（Swagger）: `http://localhost:8000/docs`

停止する場合:

```bash
cd src
docker compose down
```

### 2) 定時ジョブを手動実行（Docker）

Docker Compose で API コンテナを起動した状態で、必要なジョブだけ実行します。

```bash
cd src

# 保有銘柄の株価履歴を更新し、損益を再計算
docker compose exec api uv run python -m stock.jobs.recalc_holdings

# ポートフォリオ履歴を保存し、LINE通知を送信
docker compose exec api uv run python -m stock.jobs.update_and_notify
```

### 3) Web を起動

```bash
cd src/web
sfw pnpm install
pnpm dev
```

- 起動後のURLはViteの表示（通常は `http://localhost:5173`）に従ってください
- フロントは API を同一オリジンの相対パス（`/api/*`）で叩きます。開発時は Vite の dev proxy が `http://localhost:8000` へ転送するため、環境変数の設定は不要です
- 転送先を変えたい場合のみ `API_PROXY_TARGET` を指定してください（Docker Compose では `http://api:8000` を渡しています）

### 4) Cloudflare Worker 込みで確認する（任意）

本番と同じ経路（Workerが `/api/*` をプロキシする形）を手元で再現したい場合のみ実行します。

```bash
cd src/web
printf 'API_ORIGIN=http://localhost:8000\n' > .dev.vars
pnpm build && pnpm cf-dev
```

`.dev.vars` は gitignore 済みです。バックエンドのURLが入るためコミットしないでください。

## 開発（詳細）

### Backend（`src/api`）

前提: Python（3.13+）、`uv`、`sfw`、DB（Docker or 別途用意）

```bash
cd src/api
cp .env.sample .env
sfw uv sync
uv run alembic upgrade head
uv run uvicorn stock.app:app --reload --port 8000
```

注意:

- `src/docker-compose.yaml` のDBは `POSTGRES_PASSWORD=hogehoge` が固定です。DockerのDBを使う場合は
  `src/api/.env` の `DB_PASSWORD` を合わせるか、`src/docker-compose.yaml` を修正してください。
- CORSの設定は不要です。フロントは Vite の dev proxy（本番はCloudflare Worker）経由でAPIを叩くため、
  ブラウザから見て常に同一オリジンになります。

### Frontend（`src/web`）

```bash
cd src/web
pnpm dev
pnpm check
```

## 環境変数

- Backend: `src/api/.env.sample` を参考に `src/api/.env` を作成
- Frontend: 通常は設定不要。Vite の dev proxy の転送先を変える場合のみ `API_PROXY_TARGET` を指定する
- Cloudflare Worker: バックエンドのオリジンは `API_ORIGIN`。本番は `wrangler secret put API_ORIGIN`、手元は `src/web/.dev.vars` に置く（どちらもリポジトリには入れない）

## API仕様

APIエンドポイントの一覧は手書きでは管理せず、以下を正とします。

- `http://localhost:8000/docs`（Swagger UI）
- `http://localhost:8000/openapi.json`（OpenAPI）

※ フロントエンド側には参照用として `src/web/openapi.json` が同梱されています（生成/更新フローは今後整備予定）。

## ライセンス

MIT License（`LICENSE` を参照）
