# AGENTS.md

ユーザからの問いかけには必ず日本語で返答してください。

## プロジェクト概要

InvestLogixは、日本株と米国株のポートフォリオを管理するためのWebアプリケーションです。取引記録、保有株管理、配当管理、ポートフォリオ分析、LINE通知などの機能を提供します。

- **バックエンド (src/api)**: FastAPIベースのREST API
- **フロントエンド (src/web)**: React + Vite ベースのSPA

## サービスレベル

このアプリはユーザが10〜20人程度で使うことを想定しています。そのため、過度な品質は不要ですが、将来スケーリングしたときに問題になるような実装は避けます。

## 実装方針

- 過度に高品質な実装は不要
- 必要な要件をよく考え最小のコードで要件を達成することが望ましい
- 開発者は1人。自分が使う上で最低限のエラーハンドリングやセキュリティ対応を行う
- ファイル分割や関数の単一責任化など、初心者にも読みやすく理解しやすいコードにする
- 場当たり的対応はしない。問題が発生したときは根本的な解決をして人に見せて恥ずかしくないコードにする

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
├── infra/                      # Azure Bicep テンプレート
├── csv/                        # データサンプル
├── .github/workflows/          # CI/CD定義
└── openapi.json                # バックエンドAPIのOpenAPI仕様
```

---

## バックエンドAPI (src/api)

FastAPIベースのREST APIです。PostgreSQLをデータベースとして使用し、非同期処理に対応しています。

### 実装手順

1. 実装計画を立てる。セッション内ですでにプランニングが終わっている場合は不要
2. コードを実装する
3. api-test-creatorスキルを使ってテストコードを実装する
4. `uv run ruff format` でコードを整形する
5. `uv run ruff check --fix` でコードスタイルを整える
6. api-test-runnerサブエージェントでテストを行う
7. ドキュメント(AGENTS.md, README.md, .claude/skills/api-test-creator/SKILL.md)を更新する

### 実装の指針

- パッケージを追加するときはadd-python-packageスキルを利用すること

### コマンド

**注意**: 以下のコマンドは `src/api` ディレクトリで実行する必要があります。

```bash
# 開発サーバ起動
uv run uvicorn stock.app:app --reload --port 8000

# テスト実行
# （api-test-runnerサブエージェントに任せることを推奨）

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

### ディレクトリ構造

```
src/api/
├── stock/                      # メインアプリケーションコード
│   ├── app.py                  # FastAPIアプリ定義（エントリーポイント）
│   ├── models.py               # SQLAlchemyモデル定義
│   ├── schemas.py              # Pydanticスキーマ定義
│   ├── database.py             # DB接続設定
│   ├── auth.py                 # 認証ユーティリティ
│   ├── routes/                 # APIエンドポイント（ドメイン別）
│   ├── services/               # ビジネスロジック層
│   └── utils/                  # ユーティリティ関数
├── tests/                      # テストコード
│   ├── conftest.py             # 共通フィクスチャ
│   ├── api/                    # APIエンドポイントテスト
│   └── ...
└── alembic/                    # DBマイグレーション
```

### 主要な設計パターン

- **サービス層とルート層の分離**: routes/はエンドポイント定義のみ、services/にビジネスロジックを集約
- **取引と保有株の連動**: Transaction登録時にHoldingを自動更新
- **株式分割対応**: ユーザーごとに分割履歴を管理し、調整値を自動計算
- **株価時系列データ取得**: 日本株はJ-Quants API、米国株はpandas_datareaderのStooqを使用。期間（1M/3M/6M/1Y/3Y）と間隔（日足/週足/月足）を指定可能。投資信託は非対応
- **認証**: JWTトークンベース（Cookie または Authorization ヘッダー）

### データモデルの関係

- **User**: ユーザー情報（認証、LINE UserID）
- **Stock**: 銘柄の基本情報（symbol, name, market, currency, security_type）
  - **StockJPXDetail**: 日本株の詳細情報（セクター、市場区分など）
  - **StockUSDetail**: 米国株の詳細情報（GICSセクター、S&P500構成銘柄など）
- **StockSplit**: 株式分割履歴（user_id, symbol, split_date, split_ratio）
  - ユーザーごとに株式分割情報を管理
  - 分割比率: 4:1分割なら4.0、1:2併合なら0.5
  - 分割登録時に過去取引の調整値を自動計算（ユーザーの取引のみ対象）
- **Transaction**: 取引履歴（buy/sell, quantity, price, account_type, realized_pl, adjusted_price, adjusted_quantity）
  - adjusted_price: 株式分割による調整後の価格
  - adjusted_quantity: 株式分割による調整後の数量
- **Holding**: 保有銘柄の集計情報（quantity, average_cost, current_price, unrealized_pl, realized_pl, total_dividend）
  - 取引が発生するたびに自動的に再計算される
  - 調整済み値を優先使用して保有数量・平均取得単価を計算
- **Dividend**: 配当受取履歴
- **PortfolioHistory**: ポートフォリオ全体の資産推移履歴

### 認証認可

想定クライアントは以下

| クライアント | 認証方法 | 用途 |
|-------------|---------|------|
| Webフロントエンド | Cookie（httponly） | ブラウザからのアクセス |
| ユーザー端末からの直接API呼び出し | Authorization ヘッダー | スクリプトや CLI からのアクセス |
| Swagger UI (/docs) | OAuth2形式 | API テスト・開発 |

### コーディングスタイル

- **Python 3.11 以上**: 型ヒントを義務付け
- **フォーマッタ/リンタ**: Ruff（行長110文字以内）
- **命名規則**: モジュール/パッケージはsnake_case、クラスはPascalCase

---

## フロントエンド (src/web)

React + Vite ベースのSPAです。Vercelでデプロイされています。

### 実装手順

1. 実装計画を立てる。セッション内ですでにプランニングが終わっている場合は不要
2. コードを実装する
3. web-test-creatorスキルを使ってテストコードを実装する
4. `pnpm install` で依存関係を更新する
5. `pnpm check` を実行し、lint/format/typecheck/knipが通ることを確認する
6. `pnpm test`でテストを実行する
7. ドキュメント(AGENTS.md, README.md)を更新する

### 実装の指針

- バックエンドAPIを呼び出す必要が出たときはプロジェクトルートの`openapi.json`を参照する
- パッケージを追加するときはadd-npm-packageスキルを利用すること

### コマンド

**注意**: 以下のコマンドは `src/web` ディレクトリで実行する必要があります。

```bash
# 開発サーバーの起動
pnpm dev

# ビルド
pnpm build

# 型チェック、リンティング、フォーマット、依存関係チェック
pnpm check

# テスト実行
# （web-test-creatorスキルを使用することを推奨）

# プレビュー（ビルド後）
pnpm preview
```

**環境変数:**

- `VITE_API_URL`: バックエンドAPIのベースURL
  - ローカル: `http://localhost:8000`
  - `.env.local`で設定

### 技術スタック

- **Vite 6 + React 19 + TypeScript**: コア技術
- **React Router 7**: ルーティング
- **Tailwind CSS 4 + shadcn/ui**: スタイリング
- **SWR**: データフェッチング
- **Zustand**: グローバル状態管理（認証のみ）
- **Recharts**: グラフ描画
- **React Hook Form + Zod**: フォーム管理

### ディレクトリ構造

```
src/web/src/
├── main.tsx                    # エントリーポイント
├── App.tsx                     # ルーター設定
├── routes/                     # ページコンポーネント
├── components/                 # UIコンポーネント
│   ├── layout/                 # レイアウト（サイドバー、ナビなど）
│   ├── dashboard/              # ダッシュボード関連
│   └── ui/                     # shadcn/uiコンポーネント
└── lib/
    ├── api/                    # APIクライアント
    ├── stores/                 # Zustandストア
    └── format.ts               # フォーマット関数
```

### ルーティング

| パス | ページ | 説明 |
|------|--------|------|
| `/` | ダッシュボード | サマリーカード、資産推移、月次取引、月次配当 |
| `/holdings` | 保有状況 | 銘柄別保有状況テーブル |
| `/holdings/:symbol` | 銘柄詳細 | 保有サマリ、株価グラフ（投資信託除く）、取引履歴、配当履歴 |
| `/login` | ログイン | ログインページ |

---

## CI/CD

`.github/workflows/` にCI/CD定義があります。

| ワークフロー | 説明 |
|-------------|------|
| `api-ci.yml` | バックエンドのリント・型チェック |
| `api-test.yml` | バックエンドのテスト |
| `web-ci.yml` | フロントエンドのビルド・チェック |
| `appservice_deploy.yml` | Azure App Serviceへのデプロイ |
