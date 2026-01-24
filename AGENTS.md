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

## CI/CD

`.github/workflows/` にCI/CD定義があります。

| ワークフロー | 説明 |
|-------------|------|
| `api-ci.yml` | バックエンドのリント・型チェック |
| `api-test.yml` | バックエンドのテスト |
| `web-ci.yml` | フロントエンドのビルド・チェック |
| `appservice_deploy.yml` | Azure App Serviceへのデプロイ |

## 実装時の重要事項

api,webについて読み取り、作成、更新を行う場合はそれぞれ以下のドキュメントを見たうえでおこなうこと。

web → src/web/CLAUDE.md
api → src/api/CLAUDE.md

重要事項が記載されているため必ず見ること
