# InvestLogix - 株式投資ポートフォリオ管理アプリケーション

InvestLogixは、株式投資のポートフォリオを効率的に管理するためのアプリケーションです。銘柄情報の管理、取引記録、保有株の損益計算、配当管理、ポートフォリオ分析など、投資家に必要な機能を提供します。

## 主な機能

### 銘柄管理

- 日本株・米国株の銘柄情報の登録・管理
- 市場別の銘柄一覧表示
- 銘柄の詳細情報（セクター、業種など）の管理

### 取引管理

- 株式の購入・売却取引の記録
- 取引履歴の閲覧（銘柄別フィルタリング可能）
- 月次・年次の取引サマリー表示
- 複数の口座種別（NISA、特定口座など）に対応

### 保有株管理

- 保有銘柄一覧の表示
- 平均取得単価、保有数量の自動計算
- 現在価格に基づく時価評価額の表示
- 評価損益・評価損益率の計算
- 保有株の損益再計算機能

### 配当管理

- 配当金の記録・管理
- 配当履歴の閲覧（銘柄別フィルタリング可能）
- 月次の配当金集計表示

### ポートフォリオ分析

- ポートフォリオ全体のサマリー表示（総コスト、総時価評価額、未実現損益など）
- 市場別・通貨別の保有額分布
- ポートフォリオの資産推移履歴の記録・表示
- LINE通知機能によるポートフォリオ状況の定期レポート

### ユーザー管理・認証

- ユーザー認証（JWT認証）
- LINE連携機能

## 技術スタック

### バックエンド

- **言語**: Python
- **フレームワーク**: FastAPI
- **データベース**: PostgreSQL (Supabase)
- **ORM**: SQLAlchemy
- **マイグレーション**: Alembic
- **認証**: JWT (JSON Web Tokens)

### その他の機能

- LINE Messaging APIを使用した通知機能
- 株価情報の自動取得・更新

## API エンドポイント

### 認証関連

- `POST /api/v1/token` - ログイントークンの取得
- `POST /api/v1/oauth/token` - OAuth2形式でのログイントークン取得
- `POST /api/v1/users/` - 新規ユーザー登録（管理者のみ）
- `GET /api/v1/me` - 現在のユーザーの認証状態確認

### 銘柄関連

- `POST /api/v1/stocks/` - 新規銘柄の登録
- `GET /api/v1/stocks/` - 登録されている銘柄一覧の取得
- `DELETE /api/v1/stocks/{symbol}` - 指定された銘柄の削除

### 取引関連

- `POST /api/v1/transactions/` - 新規取引の登録
- `GET /api/v1/transactions/` - ユーザーの取引履歴の取得
- `GET /api/v1/transactions/monthly-summary` - 月ごとのトランザクション集計の取得
- `GET /api/v1/transactions/yearly-summary` - 年ごとのトランザクション集計の取得

### 保有株関連

- `GET /api/v1/holdings/` - ユーザーの保有銘柄一覧の取得
- `POST /api/v1/holdings/{symbol}/recalculate` - 保有株の損益の再計算
- `POST /api/v1/holdings/recalculate-all` - 保有する全銘柄の損益の一括再計算

### 配当関連

- `POST /api/v1/dividends/` - 配当情報の登録
- `GET /api/v1/dividends/` - ユーザーの配当履歴の取得
- `GET /api/v1/dividends/monthly` - 月次の配当金集計の取得

### ポートフォリオ関連

- `GET /api/v1/portfolio/summary` - ポートフォリオのサマリー情報の取得
- `POST /api/v1/portfolio/summary` - ポートフォリオのサマリー情報の更新
- `GET /api/v1/portfolio/history` - ポートフォリオの過去の履歴の取得
- `POST /api/v1/portfolio/update-and-notify` - ポートフォリオの更新とLINE通知の実行

### ユーザー関連

- `PUT /api/v1/users/me/line-user-id` - 現在ログインしているユーザーのLINE UserIDの更新

## 開発環境のセットアップ

1. リポジトリのクローン

```bash
git clone https://github.com/yourusername/InvestLogix.git
cd InvestLogix
```

2. 依存関係のインストール

```bash
cd src/api
uv sync
```

3. 環境変数の設定

`.env.example`ファイルをコピーして`.env`ファイルを作成し、必要に応じて環境変数を設定します。

```bash
cd src/api
cp .env.example .env
```

4. データベースのマイグレーション

```bash
cd src/api
alembic upgrade head
```

5. アプリケーションの起動

```bash
cd src/api
uvicorn stock.app:app --reload
```

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。
