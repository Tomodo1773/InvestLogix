# テストガイド（バックエンド）

AI がテストコードを実装するときに読む最小限のガイド。何をどこまでテストするかの方針はリポジトリルートの `AGENTS.md`「テスト方針」を参照。ここにはバックエンド固有の実装情報だけを書く。

## テスト環境

- pytest + testcontainers（PostgreSQL）
- 各テストは独立したデータベースで実行され、`db_session` フィクスチャはテスト終了後に自動ロールバックされる
- 実行は api-test-runner サブエージェント推奨（直接実行する場合は `src/api` で `uv run pytest`）

## テストの書き方

- テストデータの作成は原則 API エンドポイント経由で行う（DB に直接挿入しない）。実際のビジネスロジック（保有株の自動更新など）が動作することを保証するため
  - 取引: `create_transaction` フィクスチャ
  - 配当: `create_dividend` フィクスチャ
- `conftest.py` の共通フィクスチャを使う。複数テストで再利用するセットアップは `conftest.py` に追加する

### 認証

- 一般ユーザー: `auth_token` フィクスチャ / 管理者: `auth_admin_token` フィクスチャ
- フィクスチャを引数で受け取るだけで client に Cookie がセットされ認証済みになる（ヘッダー指定は不要）

### HTTP クライアント

- 非同期テスト: `client`（AsyncClient）/ 同期テスト: `sync_client`（TestClient）

### セットアップ済みデータのフィクスチャ

| フィクスチャ | 内容 |
|-------------|------|
| `setup_japanese_stock_data` | 8058 を 100株、3000円で買付 |
| `setup_us_stock_data` | AAPL を 10株、36054円で買付 |
| `setup_dividend_data` | 日本株・米国株の配当データ |
| `setup_portfolio_test_data` | 上記すべて（日本株・米国株・配当） |

### 外部 API のモック

- `mock_external_apis` フィクスチャが全テストに自動適用（autouse）。AlphaVantage / J-Quants / Yahoo Finance が対象
- 株価は初回と 2回目以降で異なる値を返す
  - 日本株: 1回目 3000.0円、2回目以降 3100.0円
  - 米国株: 1回目 36000.0円、2回目以降 37500.0円（円換算済み）

## テストを書かない対象

- 外部 API を実際に呼び出すテスト（すべてモック化されているため不要）
