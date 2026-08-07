# ADR 0004: 認証を Cloudflare Access に統一する

- ステータス: Accepted
- 日付: 2026-08-07
- 関連: Issue #441

## 背景

InvestLogix は FastAPI が独自 JWT を発行し、httponly Cookie で Web を認証している。ユーザー名と
Argon2id のパスワードハッシュもアプリケーション自身が管理する。

今後追加するリモート MCP サーバーは OAuth を前提に公開する。Web の独自認証を残したまま MCP 用の
OAuth だけを別に用意すると、同じ利用者に対して認証主体・セッション・ユーザー紐付けが二重になる。
一方、OAuth Authorization Server を自作すると、認可コードフロー、PKCE、クライアント登録、トークン
更新・失効など、個人利用のアプリには重いセキュリティ責務を抱えることになる。

フロントエンドはすでに Cloudflare Workers で配信し、API へのリクエストも Worker 経由で Cloud Run
へ転送している。Cloudflare Access はブラウザ向けの認証に加え、Managed OAuth により MCP
クライアントを含む非ブラウザクライアントの OAuth 認証も扱える。個人利用では Zero Trust Free の
範囲に収まるため、既存構成との親和性と運用コストの両方を満たす。

## 決定

### 認証と認可の境界

**Web と MCP の認証を Cloudflare Access に委譲する。アプリケーション内の認可は InvestLogix に残す。**

- Cloudflare Access は本人確認、ログインセッション、MCP の OAuth フローを担当する
- InvestLogix は Access が発行した署名済み JWT を検証し、`iss` と `sub` から内部の `user_id` を解決する
- `is_admin`、データ所有権、PostgreSQL RLS は引き続き InvestLogix が判定する
- Access のメールアドレスやグループを、検証なしにアプリケーション権限へ直接変換しない

Cloudflare からオリジンへ渡される `Cf-Access-Jwt-Assertion` は、JWKS による署名、issuer、audience、
有効期限を API と MCP の双方で検証する。ヘッダーが存在するだけでは信頼しない。

### Web 認証

Web 用の Access application を作成し、Web API を Access で保護する。現在の独自 JWT、ログイン Cookie、
パスワード認証、`/api/v1/token` は Access への移行時に削除し、恒久的な二重認証は設けない。

InvestLogix のログイン画面は残す。ユーザー名・パスワード入力の代わりに Access 認証を開始するボタンを
表示し、認証後にアプリケーションへ戻す。これにより認証処理を持たずに、サービス固有の入口と表示は維持する。

### MCP 認証

MCP は API とは別の Cloud Run サービスとして配置し、MCP 用の Access application で Managed OAuth を
有効にする。MCP サーバー自身は OAuth Authorization Server を実装せず、Access が認証した利用者の JWT を
Web と同じ処理で内部ユーザーへ解決する。

Web 用と MCP 用の Access application は分ける。同じ IdP とユーザー解決規則を使いながら、audience、
セッション、許可ポリシーを用途ごとに管理する。

MCP サーバーは公式 Python SDK と Streamable HTTP を使用し、既存の Service 層と RLS を再利用する。
Cloudflare Workers に業務ロジックや MCP ツールを複製しない。

### 導入単位

導入は次の2段階とする。

1. Web の独自 Cookie 認証を Cloudflare Access へ置き換える
2. Web で確立した JWT 検証とユーザー解決を再利用して、OAuth 対応 MCP サーバーを追加する

個人利用のため、各段階をさらに恒久的な移行レイヤーへ分割しない。

## 代替案

### Web の独自認証を維持し、MCP の OAuth だけ Cloudflare Access に任せる

Web と MCP で認証主体とユーザー紐付けが分かれ、ログアウト、失効、障害調査も二系統になるため採用しない。

### OAuth Authorization Server を InvestLogix に実装する

自由度は最も高いが、OAuth の安全な実装と継続運用は本アプリの本質ではない。個人利用に対して責務が重く、
既存の Cloudflare Access と重複するため採用しない。

### Auth0 などの顧客 ID 管理サービスを使用する

セルフサインアップや組織・テナント管理を行う一般向け SaaS には適している。現在は許可された本人だけが使う
アプリであり、追加サービスと運用が過剰なため採用しない。一般公開へ方針転換した場合は再検討する。

### Cloud Run IAM だけで MCP を保護する

Google Cloud 内部のサービス間認証には適しているが、一般的な MCP クライアントの OAuth ログインと Web の
認証を統一できないため採用しない。

## 影響

### 良い面

- パスワード、独自 JWT、ログイン Cookie の発行・更新・失効をアプリケーションが管理しなくてよくなる
- Web と MCP が同じ外部 ID と内部 `user_id` を使い、既存の RLS を維持できる
- MCP OAuth の仕様追従を Cloudflare Access に委譲できる
- Cloudflare Workers と Cloud Run という現在の配置を維持し、業務ロジックを Python 側に集約できる
- 個人利用では Cloudflare Zero Trust Free の範囲で運用できる

### 注意する面

- 認証可用性とユーザー入口が Cloudflare Access に依存する
- Managed OAuth は比較的新しい機能であり、仕様変更への追従が必要になる可能性がある
- Cloud Run の `*.run.app` URL をネットワーク上で公開したまま使う場合、すべての保護対象エンドポイントで
  Access JWT を検証し、Cloudflare を迂回した未認証リクエストを拒否しなければならない
- ローカル開発と自動テストでは、Production で有効化できない明示的な認証差し替え手段が必要になる
- Access の認証を通過したことはツール実行権限を意味しない。MCP の書き込み操作を追加する場合も、
  InvestLogix 側でユーザー権限と対象データを検証する

## 参考

- [Cloudflare Access: Managed OAuth](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/managed-oauth/)
- [Cloudflare Access: Validate JWTs](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/authorization-cookie/validating-json/)
- [Model Context Protocol Python SDK](https://github.com/modelcontextprotocol/python-sdk)
