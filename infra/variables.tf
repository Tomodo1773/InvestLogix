variable "project_id" {
  type        = string
  description = "Google Cloud プロジェクト ID。infra/.env に書いた TF_VAR_project_id を set -a; source .env; set +a で読み込んで注入する。"
}

variable "image_uri" {
  type        = string
  description = "Cloud Run Service / Jobs で使うコンテナイメージの完全 URI (Artifact Registry)。デプロイのたびに Cloud Build が更新するので、Terraform 側は ignore_changes で無視する。初回 import 時の値を設定する。"
}

variable "db_user" {
  type        = string
  description = "Supabase 接続ユーザー名（プロジェクト固有）。"
}

variable "db_host" {
  type        = string
  description = "Supabase の pooler ホスト。"
}

variable "cf_access_team_domain" {
  type        = string
  description = "Cloudflare Zero Trust のチームドメイン (例: example.cloudflareaccess.com)。API が Access JWT の JWKS と issuer を導出するのに使う。"
}

variable "cf_access_aud" {
  type        = string
  description = "Web 用 Cloudflare Access application の Audience タグ。他アプリ向けに発行された Access JWT の使い回しを防ぐ。"
}

variable "region" {
  type        = string
  default     = "asia-northeast1"
  description = "Google Cloud リージョン。Cloud Run / Scheduler / SA すべてここに揃える。"
}

variable "db_port" {
  type    = string
  default = "5432"
}

variable "db_name" {
  type    = string
  default = "postgres"
}

variable "service_name" {
  type    = string
  default = "investlogix-api"
}

variable "service_runtime_sa_id" {
  type    = string
  default = "investlogix-api-runtime"
}

variable "jobs_runtime_sa_id" {
  type    = string
  default = "investlogix-jobs-runtime"
}

variable "jobs_invoker_sa_id" {
  type    = string
  default = "investlogix-jobs-invoker"
}

variable "github_repository" {
  type        = string
  description = "GitHub Actions から WIF 経由でデプロイを許可するリポジトリ (owner/repo)。"
}

variable "artifact_registry_repo_id" {
  type        = string
  description = "Cloud Run が参照する Artifact Registry リポジトリ名。Cloud Build の自動生成リポを流用するためデフォルトは cloud-run-source-deploy。"
  default     = "cloud-run-source-deploy"
}

variable "alert_email" {
  type        = string
  description = "Cloud Monitoring からのジョブ失敗通知メール送信先（管理者）。"
  sensitive   = true
}
