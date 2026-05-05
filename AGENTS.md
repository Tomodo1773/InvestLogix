# AGENTS.md

ユーザからの問いかけには必ず日本語で返答してください。

## サービスレベル

このアプリはユーザが10〜20人程度で使うことを想定しています。そのため、過度な品質は不要ですが、将来スケーリングしたときに問題になるような実装は避けます。

## 実装方針

- 過度に高品質な実装は不要
- 必要な要件をよく考え最小のコードで要件を達成することが望ましい
- 開発者は1人。自分が使う上で最低限のエラーハンドリングやセキュリティ対応を行う
- ファイル分割や関数の単一責任化など、初心者にも読みやすく理解しやすいコードにする
- 場当たり的対応はしない。問題が発生したときは根本的な解決をして人に見せて恥ずかしくないコードにする
- 病的なまでの正確さよりも、常にシンプルさを優先すること。
- YAGNI、KISS、DRYを徹底せよ。
- サイクロマチック複雑度（循環的複雑度）を増大させずに済む場合を除き、後方互換性のためのシムやフォールバックパスは設けないこと。

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
├── .github/workflows/          # CI/CD定義
└── openapi.json                # バックエンドAPIのOpenAPI仕様
```

## CI/CD

`.github/workflows/` にCI/CD定義があります。

| ワークフロー | 説明 |
|-------------|------|
| `api-ci.yml` | バックエンドのリント・型チェック |
| `api-test.yml` | バックエンドのテスト |
| `web-ci.yml` | フロントエンドのビルド・チェック |
| `ruff-autofix.yml` | Ruffによるコードの自動修正とコミット（手動実行） |
| `biome-autofix.yml` | Biomeによるコードの自動修正とコミット（手動実行） |

## フロントエンド (src/web)

React + Vite ベースのSPAです。Vercelでデプロイされています。

### 実装手順

1. 実装計画を立てる。セッション内ですでにプランニングが終わっている場合は不要
2. コードを実装する
3. `pnpm install` で依存関係を更新する
4. テストコードを実装する（`src/web/docs/testing-guide.md`を参照）
5. `pnpm check` を実行し、lint/format/typecheck/knipが通ることを確認する
6. `pnpm test`でテストを実行する
7. ドキュメント(CLAUDE.md, README.md)を更新する
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
3. `uv sync'`で依存関係をインストールし、仮想環境を有効化する
4. テストコードを実装する（`src/api/docs/testing-guide.md`を参照）
5. `uv run ruff format` でコードを整形する
6. `uv run ruff check --fix` でコードスタイルを整える
7. api-test-runnerサブエージェントでテストを行う
8. ドキュメント(CLAUDE.md, README.md)を更新する
9. コミットする

### 実装の指針

- パッケージを追加するときはadd-python-packageスキルを利用すること

### コマンド

**注意**: 以下のコマンドは `src/api` ディレクトリで実行する必要があります。

```bash
# 開発サーバ起動
uv run uvicorn stock.app:app --reload --port 8000

# テスト実行
# (api-test-runnerサブエージェントに任せることを推奨)

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

想定クライアントは以下

| クライアント | 認証方法 | 用途 |
|-------------|---------|------|
| Webフロントエンド | Cookie(httponly) | ブラウザからのアクセス |
| ユーザー端末からの直接API呼び出し | Authorization ヘッダー | スクリプトや CLI からのアクセス |
| Swagger UI (/docs) | OAuth2形式 | API テスト・開発 |

### パスワードハッシュ

- **アルゴリズム**: Argon2id（OWASP推奨）
- **ライブラリ**: `pwdlib[argon2]`
- **実装ファイル**: `src/api/stock/auth.py`

### コーディングスタイル

- **Python 3.13 以上**: 型ヒントを義務付け
- **フォーマッタ/リンタ**: Ruff(行長110文字以内)
- **命名規則**: モジュール/パッケージはsnake_case、クラスはPascalCase
