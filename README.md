# InvestLogix

日本株・米国株の取引と配当を記録し、受け取った配当を含めて資産の状況を追うポートフォリオ管理アプリ。

## 概要

証券口座に散らばった取引履歴と配当金を1か所へ集め、保有銘柄の評価損益、資産推移、配当の実績をまとめて見られるようにした個人向けのWebアプリケーション。日本株と米国株、複数の口座種別（特定・NISA等）をまたいで平均取得単価と保有数量を自動計算する。ブラウザのダッシュボードで日々の状況を確認しつつ、週に一度Slackへレポートが届く。MCPサーバー経由でAIクライアントから保有状況を参照することもできる。

## 開発の背景

資産管理アプリは数多くあるものの、受け取った配当金を含めて自分の資産がどうなっているかを見られるものが見つからなかった。配当を資産の一部として扱えることを出発点に作り始めた。

## 主な機能

- **ダッシュボード** — 資産推移、保有銘柄の一覧と評価損益、通貨・市場別および業種別の構成比、配当の月次推移と銘柄別の割合、NISA枠の使用状況、週間騰落率を1画面にまとめて表示
- **取引・保有・配当の記録** — 購入と売却を口座種別ごとに記録し、平均取得単価・保有数量・評価損益を自動計算。株式分割にも対応。配当は入金履歴として蓄積し、月次と銘柄別に集計
- **CSVインポート** — SBI証券からエクスポートした約定履歴と配当金のCSVを取り込む。取り込み時に既存データとの差分を検出して新規分だけを登録するため、期間の重なるファイルを続けて取り込んでも重複しない
- **Slack週次レポート** — 定時ジョブがポートフォリオを更新し、サマリと週間騰落率の上位・下位5銘柄をSlackのDMへ送る。各銘柄がなぜ動いたのかを、OpenAIのweb検索で調べた解説として添える
- **MCPサーバー** — OAuthに対応した参照専用のMCPサーバーを公開。対応するAIクライアントから、本人の保有銘柄・取引履歴・配当履歴を参照できる

## 主な特徴・設計上のポイント

### 認証をCloudflare Accessへ委譲する

本人確認とログインセッションはCloudflare Accessが持ち、アプリはパスワードも独自トークンも保持しない。Accessを通過したリクエストにはCloudflareが`Cf-Access-Jwt-Assertion`ヘッダーを付与するため、アプリ側はJWKSで署名・issuer・audience・有効期限を検証するだけでよい。Cloud Runの`*.run.app`は公開されたままなので、この検証がCloudflareを迂回した直アクセスの防波堤も兼ねる。

### REST APIとMCPを同じ仕組みで通す

MCPクライアントの認証にはCloudflare AccessのManaged OAuthを使い、MCPサーバー自身はOAuthエンドポイントもクライアントシークレットも持たない。OAuthを経たリクエストにも、ブラウザと同じ`Cf-Access-Jwt-Assertion`がオリジンへ届く。結果としてRESTとMCPは同一の検証コードを共有し、入口の違いはFastAPIの依存性かASGIミドルウェアかだけになる。MCP側はASGI境界で認証を強制するため、`initialize`や`tools/list`も未認証では通らない。

### 認可はアプリとDBの両方で担保する

Accessが確認するのはメールアドレスまでで、アプリ内ユーザーへの解決、管理者権限、データの所有権はアプリの責務。認証済みのユーザーIDは同じDBセッションへ束縛され、PostgreSQLのRow Level Securityで他人の行が見えないようにしている。

### バックエンドURLをリポジトリにもバンドルにも置かない

フロントはAPIを常に相対パスで呼び、Cloudflare Workerが`/api/*`と`/mcp`をそれぞれのCloud Runへ転送する。転送先はWorkerのSecretにあるため、設定ファイルにもクライアントバンドルにも現れない。同一オリジンになることでCORSとサードパーティCookieの問題も消えている。

### 外部API呼び出しを日次バッチへ集約する

株価は`price_history`テーブルから読む。外部データソース（日本株はJ-Quants、米国株はTiingo、為替と米国株の銘柄情報はAlpha Vantage）への問い合わせはCloud Run Jobsの日次バッチにまとめ、APIハンドラからは外部を叩かない。画面の応答が外部APIのレート制限や遅延に左右されない。

### 無料枠を前提にした構成

ホスティングもデータベースも無料枠の範囲で動かしている。Cloudflare Workersの起動の速さとCloud Runの立ち上がりで、個人利用としては十分な体感速度が出る。

## システム構成

![本番環境の構成図](docs/architecture/architecture.svg)

矢印は主要な依存と相互作用を表しており、リクエストとレスポンスの完全な流れではない。

## 技術スタック

| 分類 | 技術 | 役割 |
| --- | --- | --- |
| フロントエンド | React / Vite / TypeScript | ダッシュボードと各管理画面のSPA |
| UI | Tailwind CSS / Radix UI / Recharts | 画面のスタイルとグラフ描画 |
| バックエンド | Python 3.13 / FastAPI / SQLAlchemy | REST APIとドメインロジック |
| MCP | MCP Python SDK (Streamable HTTP) | 参照専用ツールの公開 |
| データベース | PostgreSQL (Supabase) / Alembic | 永続化とマイグレーション |
| フロントのホスティング | Cloudflare Workers (Static Assets) | 静的配信とAPI/MCPへのプロキシ |
| バックエンドの実行環境 | Google Cloud Run / Cloud Run Jobs / Cloud Scheduler | APIとMCPの常時稼働、定時ジョブの実行 |
| 認証 | Cloudflare Access (Zero Trust) | 本人確認、ログインセッション、MCPのOAuth |
| インフラ定義 | OpenTofu | Google Cloud側のリソース管理 |
| 外部データ | J-Quants / Tiingo / Alpha Vantage | 日本株・米国株の株価、為替、銘柄情報 |
| 外部連携 | OpenAI API / Slack API | 週次レポートの解説生成とDM送信 |

## 補足

### 定時ジョブ

Cloud SchedulerがCloud Run Jobsを起動する。`recalc_holdings`は毎朝、株価を取得して`price_history`へ保存し、全保有銘柄の損益を再計算する。`update_and_notify`は毎週土曜に、ポートフォリオ履歴を保存してSlackへ通知する。

### 開発とテスト

リント・フォーマットはRuff（API）とBiome（Web）、テストはpytestとVitest。GitHub Actionsでリント、テスト、CodeQL解析を実行し、mainへのマージでCloudflare WorkersとCloud Runへ自動デプロイする。

### 依存関係の防御

サプライチェーン攻撃対策として[Socket Firewall Free](https://docs.socket.dev/docs/socket-firewall-free)を通し、依存を取得しうるコマンドは`sfw`経由で実行する。

### API仕様

エンドポイントの一覧は手書きで管理せず、FastAPIが生成するOpenAPI（ローカル起動時の`/docs`、`/openapi.json`）を正とする。

### ライセンス

MIT License（[`LICENSE`](LICENSE)）
