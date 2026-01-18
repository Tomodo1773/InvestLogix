# InvestLogix フロントエンド開発指示書

## アプリケーション概要

InvestLogixは、日本株と米国株のポートフォリオを管理するためのWebアプリケーションです。ユーザーは自分の取引記録、保有株、配当を管理し、資産推移を視覚的に確認できます。

## 実装してほしい機能

### 1. ログイン画面

- ユーザー名とパスワードでログインできる画面を実装
- サインアップ機能は不要（ユーザーは登録済み前提）
- ログイン成功後、ダッシュボード画面へ遷移
- エラーメッセージの表示（ユーザー名またはパスワードが間違っている場合）

### 2. ダッシュボード画面（ホーム画面）

ダッシュボードには以下の4つのセクションを含めてください：

#### 2.1 統計カード（上部）

4つの統計カードを横並びで表示：

1. **資産合計** - 総コスト（total_cost）を表示
2. **損益率** - 未実現損益率（total_unrealized_pl_percentage）を表示、パーセント表記
3. **評価額** - 総時価評価額（total_market_value）を表示
4. **配当総額** - 配当総額（total_dividend）を表示

各カードにはアイコンと値、ラベルを表示してください。

#### 2.2 資産推移グラフ（Changes in Assets）

- **上部グラフ（折れ線グラフ）**:
  - 資産合計値（total_cost）: 青色の折れ線
  - 市場価値（total_market_value）: 緑色の折れ線
  - 損益率（total_unrealized_pl_percentage）: 赤色の折れ線
  - 日次・月次・年次の表示切り替えボタンを設ける

- **下部グラフ（棒グラフ）**:
  - 収益（total_realized_pl）: 緑色の棒グラフ
  - 日付軸を上部グラフと揃える

#### 2.3 月次取引グラフ（Trade Monthly）

- 月ごとの買付金額を口座種別別に表示する棒グラフ
- 口座種別:
  - NISA(つみたて投資枠): オレンジ色
  - NISA(成長投資枠): 赤色
  - ジュニアNISA: 青色
  - 旧NISA: 黄色
  - 特定: その他の色
- X軸: 年月（例: 2021/01, 2021/02, ...）
- Y軸: 金額

#### 2.4 月次配当グラフ（Dividend Monthly）

- 月ごとの配当金額を表示する棒グラフ
- 総配当額: 緑色の棒グラフ
- X軸: 年月（例: 2021/01, 2021/02, ...）
- Y軸: 金額

## 利用するAPI

バックエンドAPIは `https://app-boyebeez7jzos.azurewebsites.net` で稼働しています。

### 認証API

#### POST /api/v1/token

ログイン用のエンドポイント。

**リクエスト:**
```json
{
  "username": "string",
  "password": "string"
}
```

**レスポンス:**
```json
{
  "access_token": "string",
  "token_type": "bearer"
}
```

**補足:**
- 認証成功時、アクセストークンがレスポンスボディとCookieの両方に返却されます
- 以降のリクエストでは、Cookieの`token`または`Authorization: Bearer {token}`ヘッダーを使用してください

#### GET /api/v1/me

現在のユーザー情報を取得するエンドポイント（トークン検証用）。

**レスポンス:**
```json
{
  "user_id": 0,
  "username": "string",
  "email": "string",
  "created_at": "2024-01-15T10:30:00+09:00",
  "line_user_id": "string",
  "is_admin": false
}
```

### ダッシュボード用API

#### GET /api/v1/portfolio/summary

ポートフォリオのサマリー情報を取得。

**レスポンス:**
```json
{
  "total_cost": 0,
  "total_market_value": 0,
  "total_unrealized_pl": 0,
  "total_unrealized_pl_percentage": 0,
  "total_realized_pl": 0,
  "total_dividend": 0,
  "holdings_by_market": {
    "JPX": 0,
    "US": 0
  },
  "holdings_by_currency": {
    "JPY": 0,
    "USD": 0
  }
}
```

#### GET /api/v1/portfolio/history

ポートフォリオの過去の履歴を取得（資産推移グラフ用）。

**レスポンス:**
```json
[
  {
    "date": "2024-01-15T00:00:00+09:00",
    "total_cost": 0,
    "total_market_value": 0,
    "total_unrealized_pl": 0,
    "total_unrealized_pl_percentage": 0,
    "total_realized_pl": 0,
    "total_dividend": 0
  }
]
```

**補足:**
- 日付順（昇順）でソートされています
- フロントエンド側で日次・月次・年次のフィルタリングを実装してください

#### GET /api/v1/transactions/monthly-summary

月ごとの取引集計を取得（月次取引グラフ用）。

**レスポンス:**
```json
[
  {
    "year": 2024,
    "month": 1,
    "total_purchase": {
      "NISA(成長投資枠)": 100000,
      "NISA(つみたて投資枠)": 50000,
      "特定": 30000
    }
  }
]
```

**補足:**
- `total_purchase`は口座種別ごとの買付金額の辞書です
- 口座種別: `NISA(成長投資枠)`, `NISA(つみたて投資枠)`, `ジュニアNISA`, `旧NISA`, `特定`

#### GET /api/v1/dividends/monthly

月次の配当金集計を取得（月次配当グラフ用）。

**レスポンス:**
```json
[
  {
    "year": 2024,
    "month": 1,
    "total_dividend": 5000
  }
]
```

## デザイン方針

### カラーテーマ

アプリケーションのfaviconから抽出したカラーパレットを使用してください：

- **プライマリカラー**: `#2D9B81` (ティール/エメラルドグリーン) - メインの緑色
- **セカンダリカラー**: `#F5A623` (オレンジ/ゴールド) - アクセントカラー
- **背景色**: `#F5F5F5` (ライトグレー) - メインの背景
- **カード背景**: `#FFFFFF` (白) - カードやパネルの背景
- **テキスト**: `#333333` (ダークグレー) - メインテキスト
- **成功/プラス**: `#4CAF50` (グリーン) - プラスの損益表示
- **エラー/マイナス**: `#F44336` (レッド) - マイナスの損益表示

### レイアウト

- レスポンシブデザインを採用し、PC・タブレット・スマートフォンに対応
- 統計カードはグリッドレイアウトで配置（PC: 4列、タブレット: 2列、スマホ: 1列）
- グラフは画面幅いっぱいに表示し、適切な余白を設ける

### フォント

- 数値: モダンなサンセリフ体（例: Roboto, Inter, Noto Sans JP）
- 日本語テキスト: Noto Sans JP または system-ui

### グラフライブラリ

- Chart.js, Recharts, または ApexCharts などの軽量なグラフライブラリを推奨
- グラフは適切なアニメーションとツールチップを実装してください

### UI/UXの推奨事項

- ローディング状態を明示的に表示
- エラーハンドリングを適切に実装し、ユーザーにわかりやすいメッセージを表示
- 損益のプラス/マイナスを色で区別（プラス: 緑、マイナス: 赤）
- 金額は3桁ごとにカンマ区切りで表示（例: ¥1,234,567）
- パーセント表記は小数点第1位まで表示（例: 57.3%）

## 技術スタック

このプロジェクトは、モダンで最新の技術を採用します。[podcast-queue](https://github.com/Tomodo1773/podcast-queue) の技術スタックを参考にしています。

### コアフレームワーク・ランタイム

- **ランタイム・パッケージマネージャー**: Bun
- **フレームワーク**: Next.js 16 (App Router)
- **UIライブラリ**: React 19
- **言語**: TypeScript

### スタイリング・UI

- **CSSフレームワーク**: Tailwind CSS 4
- **コンポーネントライブラリ**: shadcn/ui
- **UIプリミティブ**: Radix UI
- **アイコン**: Lucide Icons

### グラフライブラリ

- **推奨**: Recharts（Reactと相性が良く、shadcn/uiでもよく使われる）
- **代替**: Chart.js / ApexCharts

### 開発ツール・品質保証

- **フォーマッター・リンター**: Biome（Prettier + ESLintの代替、高速）
- **テストフレームワーク**: Vitest（Vite/Bunと相性が良い）
- **未使用コード検出**: Knip（オプション）

### 状態管理・データフェッチング

- **状態管理**: Zustand（軽量でモダン）
- **HTTPクライアント**: Fetch API（標準、Next.jsと統合が良い）
- **データフェッチング**: TanStack Query (React Query) を推奨（キャッシュ・再検証機能が強力）

## プロジェクトセットアップ

### Bunのインストール

```bash
# macOS/Linux
curl -fsSL https://bun.sh/install | bash

# Windows (PowerShell)
powershell -c "irm bun.sh/install.ps1 | iex"
```

### プロジェクトの作成

```bash
# Next.jsプロジェクトの作成
bunx create-next-app@latest investlogix-frontend --typescript --tailwind --app

# 依存関係の追加
cd investlogix-frontend
bun add zustand @tanstack/react-query recharts
bun add -d @biomejs/biome vitest @vitejs/plugin-react

# shadcn/uiのセットアップ
bunx shadcn@latest init
```

### 開発コマンド

```bash
# 開発サーバー起動
bun dev

# ビルド
bun run build

# 本番サーバー起動
bun start

# Biomeでフォーマット
bun biome format --write .

# Biomeでリント
bun biome check --write .

# テスト実行
bun test
```

## その他の考慮事項

### 認証状態の管理

- ログイン状態をローカルストレージまたはセッションストレージに保存
- トークンの有効期限切れを検知し、自動的にログイン画面にリダイレクト
- 未認証ユーザーがダッシュボードにアクセスした場合、ログイン画面にリダイレクト

### データの更新頻度

- ダッシュボード表示時に自動的にデータを取得
- 手動更新ボタンを設けても良い（オプション）

### エラーハンドリング

- API通信エラー時の適切なエラーメッセージ表示
- 認証エラー（401）時は自動的にログイン画面にリダイレクト
- その他のエラー（500など）は汎用エラーメッセージを表示

### パフォーマンス

- 大量のデータを扱う場合は、グラフのデータポイントを適切に間引く
- 画像やアイコンは最適化して使用

---

以上の指示に基づいて、InvestLogixのフロントエンドを実装してください。デザインの細かい部分やアニメーション、インタラクションの詳細は開発者の裁量にお任せします。ユーザーにとって使いやすく、視覚的に魅力的なインターフェースを目指してください。
