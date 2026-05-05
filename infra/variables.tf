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

variable "cors_origins" {
  type        = list(string)
  description = "Cloud Run Service の CORS_ORIGINS に渡す URL リスト。"
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
  description = "Cloud Run Service / Jobs が参照する Artifact Registry リポジトリ名。Cloud Build の自動作成リポを既存資産として流用するため、デフォルトは cloud-run-source-deploy。"
  default     = "cloud-run-source-deploy"
}

variable "artifact_registry_image_name" {
  type        = string
  description = "Artifact Registry 内の image 名（リポジトリ配下のパス）。フル URI は LOCATION-docker.pkg.dev/PROJECT/REPO/IMAGE_NAME。"
  default     = "investlogix/investlogix-api"
}

variable "deployer_sa_id" {
  type    = string
  default = "investlogix-deployer"
}

variable "wif_pool_id" {
  type    = string
  default = "github-actions-pool"
}

variable "wif_provider_id" {
  type    = string
  default = "github-actions-provider"
}
