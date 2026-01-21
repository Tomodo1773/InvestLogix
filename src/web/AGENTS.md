# AGENTS.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 言語設定

常に日本語で回答してください。

## プロジェクト概要

InvestLogixは、日本株と米国株のポートフォリオを管理するためのWebアプリケーションです。ユーザーは取引記録、保有株、配当を管理し、資産推移を視覚的に確認できます。
別でバックエンドが存在し、このアプリはそのフロントエンドアプリです。

**アーキテクチャ:**

- **Vite + React Router**ベースのSPAとして構築
- バックエンドAPIは別途存在するため、純粋なクライアントサイドアプリケーション
- Vercelでデプロイ（SPAリライト設定済み）

## サービスレベル

このアプリはユーザが10~20人のユーザで使うことを想定しています。

## 実装方針

- 過度に高品質な実装は不要。
- 必要な要件をよく考え最小のコードで要件を達成することが望ましい。
- 開発者は1人。自分が使う上で最低限のエラーハンドリングやセキュリティ対応を行う
- ファイル分割や関数の単一責任化など、初心者にも読みやすく理解しやすいコードにする。
- ユーザは少ないが将来スケーリングしたときに問題になるような実装はしない。
- 場当たり的対応はしない。問題が発生したときは根本的な解決をして人に見せて恥ずかしくないコードにする。

## 実装の指針

- バックエンドのAPIを呼び出す必要が出たときはプロジェクトルートの`openapi.json`にバックエンドAPIの完全な仕様が記載されているためこれを参照する。長いファイルのため、必要なエンドポイントが明確なときは必要な部分だけ抜き出して参照すること
- パッケージを追加するときはadd-packageスキルを利用すること

## 実装手順

1. 実装計画を立てる。セッション内ですでにプランニングが終わっている場合は不要
2. コードを実装する
3. pnpm install で依存関係を更新する
4. pnpm run check を実行し、lint/format/typecheck/knipが通ることを確認する
5. ドキュメント(AGENTS.md,README.md)を更新する

## 開発コマンド

```bash
# 開発サーバーの起動
pnpm dev

# ビルド
pnpm build

# 型チェック、リンティング、フォーマット、依存関係チェック
pnpm check

# プレビュー（ビルド後）
pnpm preview
```

**環境変数:**

- `VITE_API_URL`: バックエンドAPIのベースURL
  - 本番: 各自の環境に応じて設定
  - ローカル: `http://localhost:8000`
  - `.env.local`で設定

## 技術スタック

### コア

- **Vite 6**: ビルドツール
- **React Router 7**: ルーティング
- **React 19**: UIライブラリ
- **TypeScript**: 型安全性を提供

### スタイリング & UI

- **Tailwind CSS 4**: CSSフレームワーク
- **shadcn/ui**: UIコンポーネントライブラリ（Radix UIベース）
- **Lucide React**: アイコンライブラリ

### データフェッチング & 状態管理

- **SWR**: データフェッチング（useSWRフックを使用）
- **Zustand**: グローバル状態管理（認証状態のみ）
- SWRをキャッシュと再検証に使用し、Zustandは認証などのUI状態のみ管理

### グラフ

- **Recharts**: グラフ描画ライブラリ（2軸グラフ対応）

### フォーム

- **React Hook Form**: フォーム管理
- **Zod**: スキーマバリデーション
- **@hookform/resolvers**: React Hook FormとZodの統合

## ルーティング

| パス | ページ | 説明 |
|------|--------|------|
| `/` | Home (ダッシュボード) | サマリーカード、資産推移、月次取引、月次配当 |
| `/holdings` | Holdings (保有状況) | 銘柄別保有状況テーブル |
| `/login` | Login | ログインページ |

## ディレクトリ構造

```
src/
├── main.tsx                    # エントリーポイント
├── App.tsx                     # ルーター設定
├── index.css                   # グローバルスタイル
├── vite-env.d.ts               # Vite型定義
├── routes/
│   ├── Home.tsx                # ダッシュボード（認証必須）
│   ├── Holdings.tsx            # 保有状況ページ（認証必須）
│   └── Login.tsx               # ログインページ
├── components/
│   ├── AuthProvider.tsx        # 認証状態の管理と保護
│   ├── LoginForm.tsx           # ログインフォーム
│   ├── ThemeProvider.tsx       # テーマプロバイダー
│   ├── layout/
│   │   ├── app-layout.tsx      # 認証済みページ用共通レイアウト
│   │   ├── sidebar.tsx         # サイドバー（PC表示）
│   │   └── mobile-nav.tsx      # モバイルナビゲーション
│   ├── dashboard/
│   │   ├── dashboard.tsx       # ダッシュボードのメインコンポーネント（SWRでデータ取得）
│   │   ├── stat-cards.tsx      # 統計カード（4つのサマリーカード）
│   │   ├── holdings-table.tsx  # 銘柄別保有状況テーブル（ソート機能付き）
│   │   ├── asset-chart.tsx     # 資産推移グラフ（2軸折れ線 + 棒グラフ）
│   │   ├── trade-chart.tsx     # 月次取引グラフ（口座種別別の棒グラフ）
│   │   └── dividend-chart.tsx  # 月次配当グラフ（棒グラフ）
│   └── ui/                     # shadcn/uiコンポーネント
└── lib/
    ├── utils.ts                # ユーティリティ関数（cn）
    ├── format.ts               # フォーマット関数
    ├── api/
    │   ├── client.ts           # APIクライアント
    │   └── types.ts            # API型定義
    └── stores/
        └── auth-store.ts       # 認証ストア（Zustand）
```

**データフローパターン:**

1. `dashboard.tsx`がSWRで4つのAPIエンドポイントからデータを取得
   - ポートフォリオサマリー
   - 資産推移履歴
   - 月次取引集計
   - 月次配当集計
2. 各コンポーネント（`stat-cards`, `asset-chart`, `trade-chart`, `dividend-chart`）にpropsでデータを渡す
3. リフレッシュボタンクリック時、`mutate`関数を呼び出して全データを再取得

**保有状況ページ:**

1. `Holdings.tsx`がSWRで保有銘柄データを取得
2. `HoldingsTable`コンポーネントにデータを渡す
3. 独立したリフレッシュボタンで保有状況のみを再取得

### レイアウト構造

- `app-layout.tsx`: サイドバー、ヘッダー、メインコンテンツエリアを含む共通レイアウト
- `sidebar.tsx`: PC表示用のサイドバー（ナビゲーションリンク）
- `mobile-nav.tsx`: モバイル表示用のナビゲーション（オーバーレイメニュー）

### 銘柄別保有状況テーブル（`holdings-table.tsx`）

- 保有銘柄を一覧表示するテーブル（保有数量0の銘柄は非表示）
- カラムヘッダークリックでソート切り替え可能
- デフォルトソート: 損益％降順
- 損益の正負で色分け表示（正: 緑、負: 赤）
- `/holdings`ページで独立して表示

**表示カラム:**
- 銘柄名/コード
- 株数
- 前日終値
- 評価額
- 損益
- 損益%

### グラフの実装

**資産推移グラフ（`asset-chart.tsx`）:**

- 上部: 2軸折れ線グラフ
  - 左Y軸（金額）: `total_cost`, `total_market_value`
  - 右Y軸（パーセント）: `total_unrealized_pl_percentage`
- 下部: 棒グラフ（`total_realized_pl`）
- 日次・月次・年次の切り替えをクライアント側で実装
  - 日次: データをそのまま表示
  - 月次: 各月の最終日のデータのみ抽出
  - 年次: 各年の最終日のデータのみ抽出

**月次取引グラフ（`trade-chart.tsx`）:**

- 口座種別ごとの買付金額を積み上げ棒グラフで表示
- 口座種別のキーが動的に変わる可能性があるため、`total_purchase`オブジェクトのキーを抽出して描画

**月次配当グラフ（`dividend-chart.tsx`）:**

- 月ごとの配当金額を棒グラフで表示

## バックエンドAPI

### 認証API

**POST `/api/v1/token`**

- **重要**: Content-Typeは`application/json`
- リクエスト: `{ "username": "xxx", "password": "xxx" }`
- 成功時: アクセストークンをレスポンスボディとCookieの両方に返却
- トークン有効期限: 30分

**GET `/api/v1/me`**

- 現在のユーザー情報を取得（認証確認用）

### ダッシュボード用API

- **GET `/api/v1/portfolio/summary`**: ポートフォリオのサマリー情報
- **GET `/api/v1/portfolio/history`**: 資産推移データ（日次）
- **GET `/api/v1/holdings/`**: 保有銘柄一覧
- **GET `/api/v1/transactions/monthly-summary`**: 月次取引集計
- **GET `/api/v1/dividends/monthly`**: 月次配当集計

**環境:**

- 本番: 各自の環境に応じて`VITE_API_URL`で設定
- ローカル: `http://localhost:8000`
- 環境変数 `VITE_API_URL` で切り替え

### API認証方式

- Cookieベースの認証を推奨（`credentials: 'include'`を設定）
- または`Authorization: Bearer {token}`ヘッダーでトークン送信
- 401エラー時は自動的にログイン画面へリダイレクト

## スタイリングとデザイン

### カラーパレット

- **プライマリ**: `#2D9B81` (ティール/エメラルドグリーン)
- **セカンダリ**: `#F5A623` (オレンジ/ゴールド)
- **成功/プラス**: `#4CAF50` (グリーン)
- **エラー/マイナス**: `#F44336` (レッド)
- **背景**: `#F5F5F5` (ライトグレー)
- **カード背景**: `#FFFFFF` (白)
- **テキスト**: `#333333` (ダークグレー)

### フォーマット関数（`src/lib/format.ts`）

- `formatCurrency`: 通貨フォーマット（デフォルトJPY、3桁カンマ区切り）
- `formatPercent`: パーセント表記（小数点第1位、符号付き）
- `formatYearMonth`: 年月フォーマット（`YYYY/MM`形式）
