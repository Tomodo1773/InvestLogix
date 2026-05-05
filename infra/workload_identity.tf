# GitHub Actions から鍵レスで Google Cloud にアクセスするための Workload Identity Federation 設定。
# - pool: GitHub OIDC を受け付ける箱
# - provider: GitHub の OIDC issuer を信頼し、claim を attribute にマッピングする
# - iam_member: 指定リポジトリの GitHub Actions に deployer SA への成り代わり権限を付与
#
# attribute_condition で repository を絞ることで、他リポから同じ provider を経由した成り代わりを防ぐ。

resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = var.wif_pool_id
  display_name              = "GitHub Actions"
  description               = "GitHub Actions から CD 用 SA への成り代わりに使う"
}

resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = var.wif_provider_id
  display_name                       = "GitHub Actions OIDC"

  attribute_condition = "assertion.repository == \"${var.github_repository}\""

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.repository" = "assertion.repository"
    "attribute.ref"        = "assertion.ref"
  }

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

# 指定リポジトリの GitHub Actions に deployer SA への workloadIdentityUser 権限を付与
resource "google_service_account_iam_member" "deployer_wif" {
  service_account_id = google_service_account.deployer.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.github_repository}"
}
