# AGENTS.md

ユーザからの問いかけには必ず日本語で返答してください。

## プロジェクト概要

InvestLogixは、日本株と米国株のポートフォリオを管理するFastAPIベースのアプリケーションです。取引記録、保有株管理、配当管理、ポートフォリオ分析、LINE通知などの機能を提供します。

## サービスレベル

このアプリはユーザが2,3人のユーザで使うことを想定しています。そのため、過度な品質は不要です

## 実装手順

1. 実装計画を立てる。セッション内ですでにプランニングが終わっている場合は不要
2. コードを実装する
3. test-creatorスキルを使ってテストコードを実装する
4. uv run ruff format でコードを整形する
5. uv run ruff check --fix でコードスタイルを整える
6. test-runnerサブエージェントでテストを行う
7. ドキュメント(AGENTS.md,README.md)を更新する

## 実装方針

- 過度に高品質な実装は不要。
- 必要な要件をよく考え最小のコードで要件を達成することが望ましい。
- 開発者は1人。自分が使う上で最低限のエラーハンドリングやセキュリティ対応を行う

## コマンド

**注意**: 以下のコマンドは `src/api` ディレクトリで実行する必要があります。プロジェクトルートから実行する場合は、事前に `cd src/api` でディレクトリを移動してください。

```bash
# 開発サーバ起動
uv run uvicorn stock.app:app --reload --port 8000

# テスト実行
uv run pytest

# リントチェック
uv run ruff check --fix

# フォーマットチェック
uv run ruff format --check

# マイグレーション作成
uv run alembic revision --autogenerate -m "説明"

# マイグレーション適用
uv run alembic upgrade head

# マイグレーションロールバック
uv run alembic downgrade -1
```

## ディレクトリ構造

- `src/api/stock/` - メインアプリケーションコード
  - `app.py` - FastAPIアプリケーション定義、ルーター設定（エントリーポイント）
  - `models.py` - SQLAlchemyモデル定義（Stock, User, Holding, Transaction, Dividend, PortfolioHistoryなど）
  - `schemas.py` - Pydanticスキーマ定義（リクエスト/レスポンスの検証）
  - `database.py` - データベース接続設定、セッション管理（`pydantic-settings` で型安全に管理）
  - `auth.py` - 認証関連のユーティリティ（JWT検証など）
  - `routes/` - APIエンドポイント定義（認証・取引・配当などのドメイン別に分割）
    - `auth.py`, `stocks.py`, `transactions.py`, `holdings.py`, `dividends.py`, `portfolio.py`, `users.py`
    - 各ルーターは `APIRouter(prefix="/api/v1/...")` を定義
  - `services/` - ビジネスロジック層（データベースアクセスはここで実施）
    - `stock_service.py` - 銘柄登録・管理
    - `transaction_service.py` - 取引登録・集計
    - `holding_service.py` - 保有株の損益計算・株価取得
    - `dividend_service.py` - 配当管理
    - `portfolio_service.py` - ポートフォリオ分析
    - `auth_service.py` - ユーザー認証・登録
    - `jquants_service.py` - J-Quants API連携（日本株の株価・企業情報取得）
    - `alphavantage_service.py` - AlphaVantage API連携（米国株情報・為替レート取得）
    - `investment_trust_service.py` - 投資信託の基準価額取得（スクレイピング）
    - `notification_service.py` - LINE通知機能
  - `utils/` - ユーティリティ関数
    - `cache.py` - キャッシュ機能（ユーザー情報など、TTL=5分）
- `src/api/tests/` - テストコード
  - `conftest.py` - テスト用のフィクスチャ定義（データベース、認証トークン、モックなど）
  - `api/` - APIエンドポイントの統合テスト
  - `auth/` - 認証機能のテスト
  - `jquants/` - J-Quants API連携のテスト（外部APIのモックを担当）
- `src/api/alembic/` - データベースマイグレーション
  - `alembic.ini` - マイグレーションメタデータ
  - `env.py` - マイグレーション設定
  - `versions/` - マイグレーションスクリプト（命名規則: `<timestamp>_<slug>.py`）
- `src/scripts/` - データインポート等のスクリプト（`import_dividends.py`, `import_transactions.py`, `register_symbols.py`）
- `infra/` - Azure Bicep テンプレート（インフラ定義）
- `.github/workflows/` - CI/CD定義（`appservice_deploy.yml`, `ruff.yml`）
- `dividends.csv`, `trades.csv` - 共有データサンプル
- `src/api/test.db` - ローカル検証用の SQLite スナップショット（コミット前に差分の妥当性をレビュー）

### データモデルの関係

- **User**: ユーザー情報（認証、LINE UserID）
- **Stock**: 銘柄の基本情報（symbol, name, market, currency, security_type）
  - **StockJPXDetail**: 日本株の詳細情報（セクター、市場区分など）
  - **StockUSDetail**: 米国株の詳細情報（GICSセクター、S&P500構成銘柄など）
- **Transaction**: 取引履歴（buy/sell, quantity, price, account_type, realized_pl）
- **Holding**: 保有銘柄の集計情報（quantity, average_cost, current_price, unrealized_pl, realized_pl, total_dividend）
  - 取引が発生するたびに自動的に再計算される
- **Dividend**: 配当受取履歴
- **PortfolioHistory**: ポートフォリオ全体の資産推移履歴

### 重要な設計パターン

#### サービス層とルート層の分離

- `routes/` は FastAPI エンドポイントの定義のみを行う（依存性注入は FastAPI の `Depends` を使用）
- `services/` にビジネスロジックを集約
- データベースアクセスはサービス層で実施

#### 取引と保有株の連動

- 取引（Transaction）が登録されると、`transaction_service.py` が自動的に保有株（Holding）を更新
- 買付時: `_handle_buy_transaction` で保有数量と平均取得単価を再計算
- 売却時: `_handle_sell_transaction` で保有数量を減らし、実現損益（realized_pl）を計算して Transaction に記録
- 保有株の損益再計算は `holding_service.py` の `update_single_holding_pl` で実施

#### 株価取得の仕組み

- 日本株: `holding_service.py` の `get_japan_stock_price` が J-Quants API を使用
- 米国株: `holding_service.py` の `get_us_stock_price` が pandas_datareader（Yahoo Finance）を使用、円換算は AlphaVantage API
- 投資信託: `investment_trust_service.py` がスクレイピングで基準価額を取得

#### テストのフィクスチャ構成

- `conftest.py` に共通フィクスチャを定義（pytest-asyncio のデフォルトスコープは `function`）
- `setup_database`: 各テストで PostgreSQL テスト用データベースを初期化（pytest-postgresql 使用）
- `db_session`: テスト用のデータベースセッション（トランザクション内で実行され、テスト終了後に自動ロールバック）
- `client`: FastAPI の非同期テストクライアント（`AsyncClient` と `app` フィクスチャを通じて検証）
- `auth_token`, `auth_admin_token`: 認証済みユーザーのトークン
- `mock_external_apis`: 外部 API（J-Quants, AlphaVantage, Yahoo Finance）をモック化（autouse=True）
- `setup_japanese_stock_data`, `setup_us_stock_data`: テスト用の取引データ作成
- `create_transaction`, `create_dividend`: テストデータ登録用のユーティリティフィクスチャ

#### 認証認可

##### 想定クライアント

| クライアント | 認証方法 | 用途 |
|-------------|---------|------|
| Webフロントエンド | Cookie（httponly） | ブラウザからのアクセス |
| ユーザー端末からの直接API呼び出し | Authorization ヘッダー | スクリプトや CLI からのアクセス |
| Swagger UI (/docs) | OAuth2形式 | API テスト・開発 |

##### 認証（Authentication）

- **JWT トークンベース**: `python-jose` でトークン生成・検証、有効期限30分
- **パスワード管理**: `passlib` + `bcrypt` でハッシュ化
- **トークン取得**: `POST /api/v1/token` にユーザー名・パスワードを送信
- **認証済みリクエスト**: Cookie の `token` または `Authorization: Bearer {token}` ヘッダーを使用
- **関連コード**: `auth.py` の `get_current_user` で認証ユーザーを取得（キャッシュ機能あり、TTL=5分）

##### 認可（Authorization）

- **エンドポイント保護**: 保護が必要なエンドポイントは `Depends(get_current_user)` で認証ユーザーを取得
- **データアクセス制御**: サービス層で `user_id` によるフィルタリングを実施（RLSは未使用）
- **管理者権限**: `get_current_admin_user` で管理者限定エンドポイントを保護

#### データベース接続

- PostgreSQL + SQLAlchemy（非同期: `AsyncSession`, `create_async_engine`）
- `database.py` で接続設定を管理
- プールクラスは `NullPool` に設定（pool_pre_ping=True）

## コーディングスタイル

- **Python 3.11 以上**: 型ヒントを義務付け、非同期処理は `async def` と `Awaitable` を明示
- **フォーマッタ／リンタ**: Ruff
  - `uv run ruff format` で整形
  - `uv run ruff check --fix` で軽微な違反を自動修正
  - 行長は **110 文字以内**
  - 長い SQL は triple-quoted 文字列にまとめる
- **命名規則**:
  - モジュール・パッケージ: snake_case
  - クラス: PascalCase
  - 環境定義は `database.py` の `Settings` クラスに集約し、`.env` から読み込む値は `pydantic-settings` で型安全に管理
