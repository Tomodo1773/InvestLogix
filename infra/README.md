# infra/ — Google Cloud インフラ (OpenTofu)

InvestLogix の本番 Google Cloud リソース（API/MCP Cloud Run Service / Jobs / Scheduler / Service Accounts / Secret Manager IAM）を OpenTofu で管理する。

> CLI は `tofu`。HCL は Terraform 互換なので、`hashicorp/google` プロバイダ等はそのまま使える。

## 用語ミニ解説

このドキュメントで頻出する用語:

- **state**: OpenTofu が「いま何が作られていて、それぞれどんな設定か」を記録するファイル。GCS バケットに置く。
- **backend**: state の置き場所のこと。`backend "gcs" {}` で GCS を指定。
- **provider**: Google Cloud API を叩くためのプラグイン。`hashicorp/google` を使う。`tofu init` で自動ダウンロードされる。
- **SA (Service Account)**: Google Cloud の「プログラム用アカウント」。Cloud Run などが「この権限で動く」を表す主体。
- **`tofu plan`**: 「もし apply したら何が変わるか」をドライランで表示するコマンド。**実行しても何も変わらない**。
- **`tofu apply`**: plan で出た差分を実際に適用するコマンド。`yes` を打つまでは適用されない。

## 構成

| ファイル | 役割 |
|---|---|
| `versions.tf` | OpenTofu / Provider バージョン制約、GCS backend 宣言 |
| `variables.tf` | 入力変数 |
| `locals.tf` | ジョブ・スケジュール・シークレットの一覧（map 化） |
| `service_accounts.tf` | ランタイム / invoker / CD deployer の Service Account と IAM |
| `secrets.tf` | 既存シークレットの data 参照と IAM 付与 |
| `cloud_run_service.tf` | API 用 Cloud Run Service |
| `cloud_run_mcp.tf` | MCP 用 Cloud Run Service（APIと同じイメージ、別プロセス） |
| `cloud_run_jobs.tf` | バッチジョブ × 2 と invoker IAM |
| `cloud_scheduler.tf` | Cloud Scheduler × 2（OAuth 認証で Job をキック） |
| `artifact_registry.tf` | コンテナイメージ置き場 |
| `workload_identity.tf` | GitHub Actions が鍵レスで成り代わるための WIF |
| `monitoring.tf` | Cloud Run Jobs の失敗を検知する Notification Channel と Alert Policy |
| `outputs.tf` | 最小限の output（sensitive） |

## 設計方針

### 公開リポジトリ向けの秘匿
- プロジェクト ID・Supabase ホスト等の識別子は `variable` 化し、`infra/.env` に書いた `TF_VAR_*` を `set -a; source .env; set +a` で読み込んで注入する（`TF_VAR_*` は OpenTofu でもそのまま読まれる）。
- Secret 値は Secret Manager に置き、`data "google_secret_manager_secret"` で参照のみ。state には機密値が乗らない（state 自体も非公開 GCS バケットに置く）。
- state バックエンドのバケット名は `backend.hcl`（gitignore 対象）に書き、`tofu init -backend-config backend.hcl` で渡す。`.tf` には書かない。PowerShell は `-flag=value` を2つの引数に割ってしまうため、`=` ではなくスペースで区切る。

### GitHub Actions CD との役割分担
- コンテナイメージタグ (`<image>:<commit-sha>`) は GitHub Actions の `api-cd.yml` が docker push → API/MCPの `gcloud run deploy` / `gcloud run jobs update` で直接反映する。
- OpenTofu は image を `ignore_changes` で無視する。**OpenTofu は構造（env, SA, scaling, schedule, WIF, AR）を管理、GitHub Actions は image を管理。**
- 同じ理由で Cloud Run の `client` / `client_version` / `revision` 等の自動更新フィールドも無視する。

### 認証 (Cloudflare Access)
- Web の認証は Cloudflare Zero Trust の Access application が担当する。**Zero Trust ダッシュボードでの手動設計**で、OpenTofu 管理外（Google Cloud のリソースではないため）。
- Access で保護するのは Cloudflare Workers 側のドメイン全体。`/api/*` も同じドメインを通るので、Worker が受け取った `Cf-Access-Jwt-Assertion` をそのまま Cloud Run へ転送する。
- Cloud Run の `*.run.app` は公開されたままなので、**API 側が全リクエストで Access JWT の署名・issuer・audience・有効期限を検証する**。Cloudflare を迂回した直アクセスはここで 401 になる。
- 検証に必要な 2 つの値を Cloud Run に env で渡す。秘密ではないが環境依存なので `.env` の `TF_VAR_*` で注入する:

  | 変数 | 取得元 |
  |---|---|
  | `TF_VAR_cf_access_team_domain` | Zero Trust → Settings → Custom Pages のチームドメイン (`<team>.cloudflareaccess.com`) |
  | `TF_VAR_cf_access_aud` | Zero Trust → Access → Applications → 対象アプリの **Application Audience (AUD) Tag** |

- Access application を作り直すと AUD タグが変わる。変えたら `.env` を更新して `tofu apply` する。
- MCP は専用ホストの `/mcp` を Worker から別Cloud Runへ転送する。Access applicationもWeb用と分け、Managed OAuthを有効にする。
- Managed OAuthのアクセストークンはCloudflare側で利用者へ解決され、オリジンにはWebと同じ `Cf-Access-Jwt-Assertion` が届く。MCP側も署名・issuer・専用AUDを検証する。

### MCPの初期構築

1. MCP用ホスト名（例: `mcp.example.com`）を決め、同じWorkerのCustom Domainとして追加する。
2. Zero Trust → Access controls → AI controls → MCP servers で `https://<MCPホスト>/mcp` を登録し、Webと同じIdP/許可ポリシーを設定する。
3. 作成したMCP applicationのAdvanced settingsでManaged OAuthを有効化する。ローカルクライアントを使う場合はlocalhost/loopback redirectも許可する。
4. MCP applicationのAUDを `TF_VAR_cf_access_mcp_aud` に設定し、`tofu apply` で専用Cloud RunとSAを作る。
5. `tofu output -raw mcp_service_uri` の値を `cd src/web && pnpm wrangler secret put MCP_ORIGIN` でWorker Secretへ登録する。
6. MCP InspectorまたはOAuth対応MCPクライアントから `https://<MCPホスト>/mcp` へ接続し、ブラウザ認証後に3つの参照ツールが見えることを確認する。

MCPのAccess token lifetimeは5〜15分、grant sessionは1〜2週間を目安にする。OAuthはAccessが提供するため、MCPサーバー自身にOAuthエンドポイントやクライアントシークレットは置かない。

Zero Trustダッシュボード側のツール一覧は約2時間ごとのバックグラウンド同期で更新されるため、登録直後は空のことがある。空のままなら、サーバーのステータスとCloud Runのログ（401ならJWT検証、403なら`users`未登録）を確認する。

### CD 用リソースと GitHub Actions Variables の同期
- WIF / Artifact Registry / Deployer SA は OpenTofu 管理下にある。
- ワークフロー側は GCP プロジェクト ID 等の識別子を YAML に書かない（public リポのため）。`tofu output` の値を GitHub の **Settings → Secrets and variables → Actions → Variables** に手動で登録する。
- 必要な Variables: `WIF_PROVIDER`, `DEPLOYER_SA`, `IMAGE_BASE`, `GCP_REGION`, `SERVICE_NAME`, `MCP_SERVICE_NAME`。
- 取得手順:
  ```bash
  cd infra
  set -a; source .env; set +a
  tofu output -raw wif_provider
  tofu output -raw deployer_sa_email
  tofu output -raw image_base
  ```
  これらの値と、`var.region` (`asia-northeast1`) / `var.service_name` (`investlogix-api`) / `var.mcp_service_name` (`investlogix-mcp`) を Variables に登録する。WIF / AR / SA の構成を変えたときだけ再同期すればよい。

---

# 通常運用

## 前提

- gcloud CLI 認証済み（`gcloud auth login` + `gcloud auth application-default login` の **両方**）
- `infra/.env` に `TF_VAR_*` を設定済み（テンプレートは `infra/.env.example`）
- `infra/backend.hcl` に state バケット名を設定済み
- 作業開始時に環境変数を読み込む:
  ```bash
  cd infra
  set -a; source .env; set +a
  ```
  ターミナルを開き直したら都度実行する。

## 構成変更（env 追加、CPU 変更、スケジュール変更など）

```bash
cd infra
# *.tf を編集
tofu plan        # 差分確認
tofu apply       # yes と回答
git add infra/*.tf
git commit -m "..."
```

## 新規ジョブの追加

1. `src/api/stock/jobs/<new>.py` を実装
2. `infra/locals.tf` の `jobs` map と `schedules` map に 1 行ずつ追加
3. `tofu plan` → `tofu apply`

invoker IAM は `for_each` で自動付与されるので追加作業は不要。

## Secret 値の更新

OpenTofu は Secret 値を管理しない。値の追加は gcloud で:

```bash
read -rs VALUE && echo
printf '%s' "$VALUE" | gcloud secrets versions add DB_PASSWORD --data-file=-
unset VALUE
```

`:latest` 参照なので Cloud Run / Jobs の再 apply は不要（次回実行から新値が使われる）。

## イメージのデプロイ

main への push で `.github/workflows/api-cd.yml` が起動し、build → push → `gcloud run deploy` (API/MCP) → `gcloud run jobs update` (Jobs) を 1 本のワークフローで実行する。OpenTofu は image を `ignore_changes` しているので何もしない。

## Artifact Registry の初回 import

既存の `cloud-run-source-deploy` リポを OpenTofu 管理下に取り込む（既に Cloud Build が自動作成済みのため、新規作成ではなく import）:

```bash
cd infra
set -a; source .env; set +a
tofu import google_artifact_registry_repository.api \
  projects/$TF_VAR_project_id/locations/$TF_VAR_region/repositories/$TF_VAR_artifact_registry_repo_id
tofu plan   # 破壊的差分が無いことを確認
tofu apply
```

## 全削除（やり直したいとき）

```bash
cd infra
tofu destroy
```

これは Service / Jobs / Scheduler / SA / IAM を全部消す。Secret Manager のシークレット本体は OpenTofu 管理外なので消えない。

---

# トラブルシュート

| 症状 | 原因 / 対応 |
|---|---|
| `tofu plan` で `Error: Provider produced inconsistent final plan` | Provider バージョン更新で挙動が変わった可能性。`tofu init -upgrade` で再 init |
| `tofu apply` で IAM 反映エラー | 数分置いて再 apply。Google Cloud 側の IAM 反映遅延 |
| `Error: No value for required variable` (TF_VAR_xxx 系) | `.env` を読み込んでいない。`set -a; source .env; set +a` を実行 |
| state ロック取得失敗 | 別端末で `tofu plan/apply` 中。終わるのを待つか、緊急時のみ `tofu force-unlock <LOCK_ID>` |
| `Error: Failed to get existing workspaces: querying Cloud Storage failed` | ADC が無い。`gcloud auth application-default login` をやり直す |
