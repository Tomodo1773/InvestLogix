# infra/ — Google Cloud インフラ (OpenTofu)

InvestLogix の本番 Google Cloud リソース（Cloud Run Service / Jobs / Scheduler / Service Accounts / Secret Manager IAM）を OpenTofu で管理する。

旧 Azure Bicep ファイルは `azure-bicep/` 配下に退避済み（参照のみ）。

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
| `service_accounts.tf` | 3 つの Service Account |
| `secrets.tf` | 既存シークレットの data 参照と IAM 付与 |
| `cloud_run_service.tf` | API 用 Cloud Run Service |
| `cloud_run_jobs.tf` | バッチジョブ × 3 と invoker IAM |
| `cloud_scheduler.tf` | Cloud Scheduler × 3（OAuth 認証で Job をキック） |
| `outputs.tf` | 最小限の output（sensitive） |

## 設計方針

### 公開リポジトリ向けの秘匿
- プロジェクト ID・Supabase ホスト・CORS 用 URL 等の識別子は `variable` 化し、`infra/.env` に書いた `TF_VAR_*` を `set -a; source .env; set +a` で読み込んで注入する（`TF_VAR_*` は OpenTofu でもそのまま読まれる）。
- Secret 値は Secret Manager に置き、`data "google_secret_manager_secret"` で参照のみ。state には機密値が乗らない（state 自体も非公開 GCS バケットに置く）。
- state バックエンドのバケット名は `backend.hcl`（gitignore 対象）に書き、`tofu init -backend-config=backend.hcl` で渡す。`.tf` には書かない。

### Cloud Build 自動デプロイとの役割分担
- コンテナイメージタグ (`<image>:<commit-sha>`) は Cloud Build の継続的デプロイが直接 Cloud Run に反映する。
- OpenTofu は image を `ignore_changes` で無視する。**OpenTofu は構造（env, SA, scaling, schedule）を管理、Cloud Build は image を管理。**
- 同じ理由で `gcb-build-id` 等の Cloud Build 由来ラベルも無視する。

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

Cloud Build トリガーで自動。Cloud Run Jobs への反映は `scripts/update-cloud-run-jobs.sh`。OpenTofu は image を `ignore_changes` しているので何もしない。

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
