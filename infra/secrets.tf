# Secret Manager のシークレット本体は手動運用（gcloud secrets create）で既に存在する。
# Terraform は data source で参照し、Service / Jobs ランタイム SA への secretAccessor 付与だけを管理する。

data "google_secret_manager_secret" "all" {
  for_each  = local.all_secrets
  secret_id = each.value
}

# Cloud Run Service ランタイム SA に対し、Service が参照する全シークレットの読取権限を付与
resource "google_secret_manager_secret_iam_member" "api_runtime" {
  for_each = toset(local.service_secrets)

  project   = data.google_secret_manager_secret.all[each.value].project
  secret_id = data.google_secret_manager_secret.all[each.value].secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.api_runtime.email}"
}

# Cloud Run Jobs ランタイム SA に対し、Jobs が参照する全シークレットの読取権限を付与
resource "google_secret_manager_secret_iam_member" "jobs_runtime" {
  for_each = toset(local.jobs_secrets)

  project   = data.google_secret_manager_secret.all[each.value].project
  secret_id = data.google_secret_manager_secret.all[each.value].secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.jobs_runtime.email}"
}
