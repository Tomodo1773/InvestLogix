resource "google_service_account" "api_runtime" {
  account_id   = var.service_runtime_sa_id
  display_name = "Cloud Run Service runtime"
}

resource "google_service_account" "mcp_runtime" {
  account_id   = var.mcp_runtime_sa_id
  display_name = "Cloud Run MCP runtime"
}

resource "google_service_account" "jobs_runtime" {
  account_id   = var.jobs_runtime_sa_id
  display_name = "Cloud Run Jobs runtime"
}

resource "google_service_account" "jobs_invoker" {
  account_id   = var.jobs_invoker_sa_id
  display_name = "Cloud Scheduler -> Cloud Run Jobs invoker"
}

resource "google_service_account" "deployer" {
  account_id   = local.deployer_sa_id
  display_name = "GitHub Actions deployer (CD)"
}

resource "google_project_iam_member" "deployer" {
  for_each = toset([
    "roles/run.admin",
    "roles/iam.serviceAccountUser",
    "roles/artifactregistry.writer",
  ])

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.deployer.email}"
}
