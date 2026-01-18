InvestLogix フロントエンド開発指示書（Vite + React Router版）

アプリケーション概要

InvestLogixは、日本株および米国株のポートフォリオを管理するためのWebアプリケーションです。ユーザーは取引履歴・保有資産・配当情報を管理し、資産推移や損益状況をダッシュボード上で視覚的に把握できます。

本プロジェクトは小規模な個人開発のSPAとして、実装速度・保守性・理解しやすさを重視します。


---

実装機能

1. ログイン画面

ユーザー名・パスワードによるログイン

サインアップ機能は不要（登録済みユーザー前提）

ログイン成功時、ダッシュボードへ遷移

認証失敗時、エラーメッセージを表示



---

2. ダッシュボード画面

2.1 統計カード（上部）

以下の4つの統計カードを表示（レスポンシブ対応）：

1. 資産合計：total_cost


2. 損益率：total_unrealized_pl_percentage（%表示、小数1桁）


3. 評価額：total_market_value


4. 配当総額：total_dividend



アイコン＋ラベル＋数値を表示

金額は**日本円（JPY）**で表示（3桁区切り）

損益はプラス/マイナスで色分け（プラスは + を付与）



---

2.2 資産推移グラフ（Changes in Assets）

上部：折れ線グラフ（2軸）

左Y軸（金額）

資産合計（total_cost）

市場価値（total_market_value）


右Y軸（割合）

損益率（total_unrealized_pl_percentage）



下部：棒グラフ

実現損益（total_realized_pl）

X軸は上部グラフと共通


表示切り替え

日次 / 月次 / 年次


集計ルール（重要）

月次・年次の資産額：その期間の最終日の値を使用

実現損益・配当：期間内の合計値を使用

日付キーは YYYY-MM-DD / YYYY-MM / YYYY の文字列で扱い、Date型依存を避ける



---

2.3 月次取引グラフ（Trade Monthly）

月ごとの買付金額を棒グラフで表示

口座種別ごとにスタック表示


口座種別（固定順・固定色）

NISA(つみたて投資枠)：オレンジ

NISA(成長投資枠)：レッド

ジュニアNISA：ブルー

旧NISA：イエロー

特定：グレー


※ 該当データが存在しない場合は0として扱う


---

2.4 月次配当グラフ（Dividend Monthly）

月ごとの配当合計を棒グラフで表示

緑色で統一



---

利用API

バックエンドAPIは https://app-boyebeez7jzos.azurewebsites.net で稼働しています。

認証

POST /api/v1/token

ログイン用エンドポイント

トークンはレスポンスBodyおよびCookieに返却される


認証方式方針（セキュア優先）

Cookie方式を採用（フロントでトークンを保持しない）

以降のAPI呼び出しは Cookieを送信して認証する

すべてのAPI呼び出しで fetch に credentials: "include" を付与

401（未認証/期限切れ）時は /login にリダイレクト


> 注意：Cookie認証をSPAで成立させるには、バックエンド側でCORSおよびCookie属性（SameSite / Secure など）が適切に設定されている必要があります。




---

GET /api/v1/me

現在ユーザー情報の取得（トークン検証用）

401時は自動的にログイン画面へリダイレクト



---

ダッシュボードAPI

以降のエンドポイント呼び出しは、Cookie認証のため credentials: "include" を付与します。

共通ベースURL：https://app-boyebeez7jzos.azurewebsites.net

共通方針：

fetch(url, { credentials: "include" })

401時：ログイン画面へリダイレクト

それ以外のエラー：汎用エラーメッセージ＋再試行導線



GET /api/v1/portfolio/summary

ポートフォリオのサマリー情報を取得（統計カード用）。

レスポンス（例）

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


---

GET /api/v1/portfolio/history

ポートフォリオの履歴を取得（資産推移グラフ用）。

レスポンス（例）

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

補足

日付順（昇順）でソート済み

フロント側で 日次 / 月次 / 年次 を切り替え

日付は +09:00 を含むため、JST前提でキー生成・表示を行う



---

GET /api/v1/transactions/monthly-summary

月次の取引集計（月次取引グラフ用）。

レスポンス（例）

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

補足

total_purchase は口座種別ごとの買付金額の辞書

口座種別（想定）：NISA(成長投資枠), NISA(つみたて投資枠), ジュニアNISA, 旧NISA, 特定

欠けているキーは 0 として扱い、表示順・色マップは固定



---

GET /api/v1/dividends/monthly

月次の配当集計（月次配当グラフ用）。

レスポンス（例）

[
  {
    "year": 2024,
    "month": 1,
    "total_dividend": 5000
  }
]


---

UI/UX方針

ローディング中はスケルトンUIを表示

エラー時は簡潔で明確なメッセージを表示

**全体のロケールは日本（日本時間・日本円）**で統一

金額：Intl.NumberFormat("ja-JP", { style: "currency", currency: "JPY" })

パーセント：小数点第1位まで

日付表示：YYYY/MM など日本向け表記


損益はプラス/マイナスで色分け（プラスは + を付与）


日付・タイムゾーン（重要）

APIの date は +09:00 を含むため、表示・集計は JST（Asia/Tokyo）前提で行う

集計キーは YYYY-MM-DD / YYYY-MM / YYYY の文字列で扱い、Date型依存を避ける



---

技術スタック

コア

ランタイム / パッケージマネージャ：Bun

ビルドツール：Vite

ルーティング：React Router

UIライブラリ：React 19

言語：TypeScript


スタイリング / UI

Tailwind CSS 4

shadcn/ui

Radix UI

Lucide Icons


データ / 状態管理

データフェッチ：TanStack Query（統一）

グローバル状態：Zustand（UI状態のみ）


グラフ

Recharts（2軸対応）


開発ツール

Biome（format + lint）

Vitest

Knip（任意）



---

プロジェクトセットアップ

bun create vite investlogix-frontend --template react-ts
cd investlogix-frontend
bun install
bun add react-router-dom zustand @tanstack/react-query recharts
bun add -d @biomejs/biome vitest


---

ルーティング構成

/login

/（dashboard）



---

補足方針

React Routerのloader/actionは使用せず、データ取得はTanStack Queryに集約

Zustandはフォーム状態・UI状態に限定

小規模SPAとして過度な抽象化は行わない



---

この指示書をもとに、保守性が高く、視認性に優れた投資管理ダッシュボードを実装してください。