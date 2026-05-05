resource "google_service_account" "api_runtime" {
  account_id   = var.service_runtime_sa_id
  display_name = "Cloud Run Service runtime"
}

resource "google_service_account" "jobs_runtime" {
  account_id   = var.jobs_runtime_sa_id
  display_name = "Cloud Run Jobs runtime"
}

resource "google_service_account" "jobs_invoker" {
  account_id   = var.jobs_invoker_sa_id
  display_name = "Cloud Scheduler -> Cloud Run Jobs invoker"
}

# GitHub Actions が WIF 経由で成り代わる CD 用 SA。
# Cloud Run Service / Jobs の image 更新と、Artifact Registry への push を行う。
resource "google_service_account" "deployer" {
  account_id   = var.deployer_sa_id
  display_name = "GitHub Actions deployer (CD)"
}

# deployer に Cloud Run Service / Jobs のデプロイ権限を付与
resource "google_project_iam_member" "deployer_run_admin" {
  project = var.project_id
  role    = "roles/run.admin"
  member  = "serviceAccount:${google_service_account.deployer.email}"
}

# Cloud Run のランタイム SA を deployer が指定できるようにする
resource "google_project_iam_member" "deployer_sa_user" {
  project = var.project_id
  role    = "roles/iam.serviceAccountUser"
  member  = "serviceAccount:${google_service_account.deployer.email}"
}

# Artifact Registry への push 権限
resource "google_project_iam_member" "deployer_ar_writer" {
  project = var.project_id
  role    = "roles/artifactregistry.writer"
  member  = "serviceAccount:${google_service_account.deployer.email}"
}
