# InvestLogix

InvestLogixは、日本株・米国株の取引/保有/配当を記録し、ポートフォリオを可視化するWebアプリケーションです。

- バックエンド: FastAPI（`src/api`）
- フロントエンド: React + Vite（`src/web`）
- DB: PostgreSQL（ローカル開発はDocker推奨）

## 主な機能

- 銘柄管理（日本株・米国株、銘柄詳細情報）
- 取引管理（購入/売却、口座種別、月次/年次サマリー）
- 保有株管理（平均取得単価・保有数量の自動計算、評価損益）
- 配当管理（配当履歴、月次集計）
- ポートフォリオ分析（資産推移、通貨/市場別の分布、サマリー）
- LINE通知（ポートフォリオ状況の通知）
- 認証（JWT）

## リポジトリ構成

```
InvestLogix/
├── src/
│   ├── api/                 # FastAPI API
│   ├── web/                 # React + Vite SPA
│   ├── docker-compose.yaml  # ローカル開発用（DB + API）
│   └── Dockerfile           # ローカルDB用（PostgreSQL）
├── infra/                   # Azure Bicep
└── csv/                     # サンプルデータ等
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

### 2) Web を起動

```bash
cd src/web
pnpm install
cp .env.local.example .env.local
pnpm dev
```

- `VITE_API_URL` が API のURL（デフォルトは `http://localhost:8000`）
- 起動後のURLはViteの表示（通常は `http://localhost:5173`）に従ってください

## 開発（詳細）

### Backend（`src/api`）

前提: Python（3.13+）、`uv`、DB（Docker or 別途用意）

```bash
cd src/api
cp .env.sample .env
uv sync
uv run alembic upgrade head
uv run uvicorn stock.app:app --reload --port 8000
```

注意:

- `src/docker-compose.yaml` のDBは `POSTGRES_PASSWORD=hogehoge` が固定です。DockerのDBを使う場合は
  `src/api/.env` の `DB_PASSWORD` を合わせるか、`src/docker-compose.yaml` を修正してください。
- フロント開発サーバのオリジンに合わせて `CORS_ORIGINS` を設定してください（Vite既定は `http://localhost:5173`）。

### Frontend（`src/web`）

```bash
cd src/web
pnpm dev
pnpm check
```

## 環境変数

- Backend: `src/api/.env.sample` を参考に `src/api/.env` を作成
- Frontend: `src/web/.env.local.example` を参考に `src/web/.env.local` を作成

## API仕様

APIエンドポイントの一覧は手書きでは管理せず、以下を正とします。

- `http://localhost:8000/docs`（Swagger UI）
- `http://localhost:8000/openapi.json`（OpenAPI）

※ フロントエンド側には参照用として `src/web/openapi.json` が同梱されています（生成/更新フローは今後整備予定）。

## ライセンス

MIT License（`LICENSE` を参照）
