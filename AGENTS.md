# InvestLogix

ユーザからの問いかけには必ず日本語で返答してください。

## サービスレベル

「**設計の質は 1,000 人規模を意識、運用コストと手段は 1 人規模に合わせる**」というバランスを取ります。

学習目的で、N+1 解消・適切なインデックス・認可境界・構造化ログ・主要ユースケースの正常系テストといった「中規模 SaaS の教科書的な品質基準」を満たすことを設計判断の軸とします。

ただし以下は個人利用の現実に合わせます。「1,000 人規模に耐えない」という理由で否定しないでください：

- インフラ・外部 API は無料プラン優先。コストが見合わない選択は採らない
- 一部の外部データ取得は規約上グレーな手段（スクレイピング等）を使うことがある（個人利用の範囲で運用する前提）
- Redis キャッシュ層、ジョブキュー、DB シャーディング等の本格的な分散システム設計は対象外。ボトルネック顕在化まで導入しない

## 実装方針

- 過度に高品質な実装は不要
- 必要な要件をよく考え最小のコードで要件を達成することが望ましい
- 開発者は1人。1,000人規模の利用を想定したエラーハンドリングとセキュリティ対応を行う
- ファイル分割や関数の単一責任化など、初心者にも読みやすく理解しやすいコードにする
- 場当たり的対応はしない。問題が発生したときは根本的な解決をして人に見せて恥ずかしくないコードにする
- 病的なまでの正確さよりも、常にシンプルさを優先すること。
- YAGNI、KISS、DRYを徹底せよ。
- サイクロマチック複雑度（循環的複雑度）を増大させずに済む場合を除き、後方互換性のためのシムやフォールバックパスは設けないこと。
- レビュー等で指摘された問題は「今回のタスクで新規に導入したものではない既存コードの問題」であっても、直すべきものは直す。「スコープ外」を理由に見送らない。

## テスト方針

- カバレッジだけを追い求めず、開発者が認知・管理できる範囲に留める
- 正常系を中心にテストを実装
- 異常系は必要最低限のものに限定
- 1人開発のため、過度な品質は追求しない
- 外部リソース中心でモック中心になるテストは見送る

## プロジェクト概要

InvestLogixは、日本株と米国株のポートフォリオを管理するためのWebアプリケーションです。取引記録、保有株管理、配当管理、ポートフォリオ分析、LINE通知などの機能を提供します。

- **バックエンド (src/api)**: FastAPIベースのREST API
- **フロントエンド (src/web)**: React + Vite ベースのSPA

## リポジトリ構成

```
InvestLogix/
├── src/
│   ├── api/                    # バックエンドAPI (FastAPI)
│   │   ├── stock/              # メインアプリケーションコード
│   │   ├── tests/              # テストコード
│   │   ├── alembic/            # DBマイグレーション
│   │   └── pyproject.toml      # Python依存関係
│   ├── web/                    # フロントエンド (React + Vite)
│   │   ├── src/                # ソースコード
│   │   └── package.json        # Node.js依存関係
│   ├── scripts/                # データインポート等のスクリプト
│   ├── Dockerfile              # APIのDockerイメージ
│   └── docker-compose.yaml     # ローカル開発用のDocker構成
├── infra/                      # Google Cloud インフラ (OpenTofu)
├── csv/                        # データサンプル
├── samples/                    # SBI証券エクスポートcsvサンプル
│   └── sbi_export_file/
│       ├── SaveFile_000001_000137.csv  # 円建て口座のサンプル(cp932エンコーディング)
│       └── yakujo20260201135112.csv    # 外貨建て口座のサンプル(cp932エンコーディング)
└── .github/workflows/          # CI/CD定義
```

## CI/CD

`.github/workflows/` にCI/CD定義があります。

| ワークフロー | 説明 |
|-------------|------|
| `api-ci.yml` | バックエンドのリント・フォーマットチェック（Ruff） |
| `api-test.yml` | バックエンドのテスト |
| `api-cd.yml` | バックエンドのCloud Runへのデプロイ（main push時） |
| `web-ci.yml` | フロントエンドのビルド・チェック |
| `web-cd.yml` | フロントエンドのCloudflare Workersへのデプロイ（main push時） |
| `codeql.yml` | CodeQLによるコード解析 |
| `agent-docs-sync.yml` | 指示ファイルとスキルの同期チェック |

Ruffのバージョンは `src/api/uv.lock` を唯一の情報源とします。CI（`api-ci.yml`）・pre-commit・ローカルの `uv run ruff` がすべて同じバージョンで動くよう、`.pre-commit-config.yaml` の `rev` も uv.lock のRuffに合わせて更新してください。

## フロントエンド (src/web)

React + Vite ベースのSPAです。Cloudflare Workers（Static Assets）でデプロイされています。

`worker/index.ts` が `/api/*` と `/mcp` を、それぞれAPI/MCP用Cloud Runへプロキシします。フロント側はAPIを**常に相対パスで叩きます**（`API_BASE_URL` のような基底URLは持ちません）。オリジンは Worker の Secret（`API_ORIGIN` / `MCP_ORIGIN`）にあり、リポジトリにもクライアントバンドルにも入れません。

- Workersランタイムの型 `worker-configuration.d.ts` は生成物なのでコミットしない（gitignore済み）。14000行超あるうえ、`wrangler types` がローカルの `.dev.vars` の変数名を取り込むためマシン間で内容が一致しない。`pnpm typecheck` が毎回先頭で生成するので、手動実行は不要（単体で回したいときは `pnpm cf-typegen`）
- `compatibility_date` は同梱 workerd がサポートする上限日以下にする。超えると `wrangler dev` が起動しない。制約は一方向（wrangler を上げると上限が上がるだけ）なので、**依存更新に追随して上げる必要はない**。日付でゲートされた挙動が欲しいときだけ意図して上げる
- `worker/` は Workers ランタイム、`src/` は DOM で型が衝突するため tsconfig を分けている。`pnpm typecheck` は両方を検査する

### 実装手順

1. 実装計画を立てる。セッション内ですでにプランニングが終わっている場合は不要
2. コードを実装する
3. `sfw pnpm install` でSocket Firewallを通して依存関係を更新する
4. テストコードを実装する（`src/web/docs/testing-guide.md`を参照）
5. `pnpm check` を実行し、lint/format/typecheck/knipが通ることを確認する
6. `pnpm test`でテストを実行する
7. ドキュメント(AGENTS.md/CLAUDE.md, README.md)を更新する
8. コミットする

### 実装の指針

- バックエンドAPIを呼び出す必要が出たときはsrc/apiを参照して仕様を確認する。
- パッケージを追加するときはadd-npm-packageスキルを利用すること

### コーディングスタイル

- **TypeScript**: 型定義を義務付け(strict mode有効)
- **フォーマッタ/リンタ**: Biome(行長110文字以内)
- **コードスタイル**:
  - インデント: スペース2文字
  - クォート: ダブルクォート
  - セミコロン: 必要な箇所のみ
  - 末尾カンマ: ES5形式
- **命名規則**:
  - コンポーネント: PascalCase
  - 関数/変数: camelCase
  - 定数: UPPER_SNAKE_CASE
  - ファイル名: kebab-case (コンポーネントはPascalCaseも可)

### コマンド

**注意**: 以下のコマンドは `src/web` ディレクトリで実行する必要があります。

```bash
# 開発サーバーの起動
pnpm dev

# 依存関係のインストール（Socket Firewall経由）
sfw pnpm install

# ビルド
pnpm build

# 型チェック、リンティング、フォーマット、依存関係チェック
pnpm check

# テスト実行
pnpm test

# プレビュー(ビルド後)
pnpm preview
```

## バックエンドAPI (src/api)

FastAPIベースのREST APIです。PostgreSQLをデータベースとして使用し、非同期処理に対応しています。

### 実装手順

1. 実装計画を立てる。セッション内ですでにプランニングが終わっている場合は不要
2. コードを実装する
3. `sfw uv sync` でSocket Firewallを通して依存関係をインストールし、仮想環境を有効化する
4. テストコードを実装する（`src/api/docs/testing-guide.md`を参照）
5. `uv run ruff format` でコードを整形する
6. `uv run ruff check --fix` でコードスタイルを整える
7. api-test-runnerサブエージェントでテストを行う
8. ドキュメント(AGENTS.md/CLAUDE.md, README.md)を更新する
9. コミットする

### 実装の指針

- パッケージを追加するときはadd-python-packageスキルを利用すること
- 設定値は `stock/database.py` の `Settings` に集約する

### コマンド

**注意**: 以下のコマンドは `src/api` ディレクトリで実行する必要があります。

```bash
# 開発サーバ起動
uv run uvicorn stock.app:app --reload --port 8000

# MCPサーバ起動（Streamable HTTP: http://localhost:8001/mcp）
uv run uvicorn stock.mcp.app:app --reload --port 8001

# 依存関係のインストール（Socket Firewall経由）
sfw uv sync

# テスト実行（api-test-runnerサブエージェントに任せることを推奨）
uv run pytest

# リントチェック
uv run ruff check --fix

# フォーマット
uv run ruff format

# マイグレーション作成
uv run alembic revision --autogenerate -m "説明"

# マイグレーション適用
uv run alembic upgrade head

# マイグレーションロールバック
uv run alembic downgrade -1
```

### 認証認可

本人確認とログインセッションは **Cloudflare Access** に委譲する。アプリはパスワードも独自トークンも持たない。判断の経緯は `docs/adr/0004-cloudflare-access-authentication.md`。

処理の流れはフレームワーク非依存の中核と、REST/MCP固有の入口に分かれる。

| ファイル | 責務 |
|---------|------|
| `stock/cloudflare_access.py` | `Cf-Access-Jwt-Assertion` の検証（JWKS取得・署名・issuer・audience・有効期限）。DBにもFastAPIにも依存しない |
| `stock/services/user_service.py` | Accessが確認済みのメールアドレスからアプリ内 `users` を解決する。JWTの `sub` はAccess applicationごとに変わりうるため紐付けキーにしない |
| `stock/user_context.py` | User解決とRLS設定を同じDBセッションへ束縛する。REST/MCP共通 |
| `stock/auth.py` | FastAPIの依存性として共通コンテキストを接続する |
| `stock/mcp/` | MCP全体へ認証を強制し、RLS済みコンテキストからService層を呼ぶ |

- 認証は `FastAPI(dependencies=[Depends(get_access_identity)])` でアプリ全体に掛ける。ルート単位で書き忘れても素通りしない
- Cloud Run の `*.run.app` は公開されたままなので、この検証がCloudflareを迂回した直アクセスの防波堤になる
- 未認証は401、Access認証済みだがアプリ未登録は403
- Swagger UI (`/docs`) が使えるのはローカルのみ。サイト側はWorkerが `/api/*` と `/mcp` しか通さず、`*.run.app` 側はAccessのヘッダーが付かない
- `is_admin`、データ所有権、PostgreSQL RLS はアプリ側の責務。Accessのメールアドレスやグループを検証なしに権限へ変換しない
- 定期ジョブはGoogle Cloud Run JobsでDB直結のため、HTTP経由のAPI認証経路は持たない
- MCPは公式Python SDKのStreamable HTTPを使い、APIとは別のCloud Runサービスで動かす。公開ツールは参照系から始める

ローカル開発とテストでの差し替えは以下。

| 用途 | 手段 |
|------|------|
| ローカル開発 | `.env` の `DEV_AUTH_EMAIL`。そのメールアドレスのユーザーとして扱う。`ENVIRONMENT=production` では設定できず、設定されていると起動時に失敗する |
| テスト | `get_access_identity` の `dependency_overrides`（`auth_user` / `auth_admin_user` フィクスチャ）。ユーザー解決とRLSは本番と同じ経路を通る |

### コーディングスタイル

- **Python 3.13 以上**: 型ヒントを義務付け
- **フォーマッタ/リンタ**: Ruff(行長110文字以内)
- **命名規則**: モジュール/パッケージはsnake_case、クラスはPascalCase

### バッチジョブ

`stock/jobs/` 配下にバッチジョブを実装しています。Google Cloud Run Jobs から `python -m stock.jobs.<job_name>` の形で起動します。

| ジョブ | 説明 |
|--------|------|
| `recalc_holdings` | 保有銘柄の最新価格を取得して `price_history` に upsert し、全 holdings の損益を再計算 |
| `update_and_notify` | ポートフォリオ全体を更新して履歴に保存し、LINE 通知を送信 |

ローカルで Docker Compose 起動中に手動実行する場合は、`src` ディレクトリで以下を実行します。

```bash
docker compose exec api uv run python -m stock.jobs.recalc_holdings
docker compose exec api uv run python -m stock.jobs.update_and_notify
```

株価は `price_history` テーブル（直近21日分を保持）から読み込みます。外部 API への問い合わせは原則として日次バッチに集約しているため、API ハンドラ側からは外部呼び出しを行わずに DB を引く設計です。

### 日時の取り扱い

- 現在時刻は `stock/utils/datetime.py` の `now_jst()` を使う。`datetime.utcnow()` や `datetime.now()` は使わない
- DB に保存する時刻はタイムゾーン付き（JST）

## 指示ファイルの同期

`AGENTS.md` と `CLAUDE.md`、`.agents/skills` と `.claude/skills` は同じ内容の別実体です。片方を変更したら、もう一方も同じ内容に揃えてください。

クローン後に `git config core.hooksPath .githooks` を実行してください。
