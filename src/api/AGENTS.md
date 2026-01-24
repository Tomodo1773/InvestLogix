# バックエンドAPI (src/api)

FastAPIベースのREST APIです。PostgreSQLをデータベースとして使用し、非同期処理に対応しています。

## 実装手順

1. 実装計画を立てる。セッション内ですでにプランニングが終わっている場合は不要
2. コードを実装する
3. `uv sync'`で依存関係をインストールし、仮想環境を有効化する
4. api-test-creatorスキルを使ってテストコードを実装する
5. `uv run ruff format` でコードを整形する
6. `uv run ruff check --fix` でコードスタイルを整える
7. api-test-runnerサブエージェントでテストを行う
8. ドキュメント(AGENTS.md, README.md, .claude/skills/api-test-creator/SKILL.md)を更新する
9. コミットする

## 実装の指針

- パッケージを追加するときはadd-python-packageスキルを利用すること

## コマンド

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

## ディレクトリ構造

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

## 主要な設計パターン

- **サービス層とルート層の分離**: routes/はエンドポイント定義のみ、services/にビジネスロジックを集約
- **取引と保有株の連動**: Transaction登録時にHoldingを自動更新
- **株式分割対応**: ユーザーごとに分割履歴を管理し、調整値を自動計算
- **株価時系列データ取得**: 日本株はJ-Quants API、米国株はpandas_datareaderのStooqを使用。期間（1M/3M/6M/1Y/3Y）と間隔（日足/週足/月足）を指定可能。投資信託は非対応
- **認証**: JWTトークンベース（Cookie または Authorization ヘッダー）

## データモデルの関係

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

## 認証認可

想定クライアントは以下

| クライアント | 認証方法 | 用途 |
|-------------|---------|------|
| Webフロントエンド | Cookie（httponly） | ブラウザからのアクセス |
| ユーザー端末からの直接API呼び出し | Authorization ヘッダー | スクリプトや CLI からのアクセス |
| Swagger UI (/docs) | OAuth2形式 | API テスト・開発 |

## コーディングスタイル

- **Python 3.11 以上**: 型ヒントを義務付け
- **フォーマッタ/リンタ**: Ruff（行長110文字以内）
- **命名規則**: モジュール/パッケージはsnake_case、クラスはPascalCase
