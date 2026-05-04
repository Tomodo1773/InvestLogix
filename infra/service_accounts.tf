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
