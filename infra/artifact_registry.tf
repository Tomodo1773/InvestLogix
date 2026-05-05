# Cloud Run のコンテナイメージ置き場。
# 既存 Cloud Build が "cloud-run-source-deploy" リポを自動生成済みのため、tofu import で取り込む:
#   tofu import google_artifact_registry_repository.api \
#     projects/$TF_VAR_project_id/locations/$TF_VAR_region/repositories/$TF_VAR_artifact_registry_repo_id
resource "google_artifact_registry_repository" "api" {
  location      = var.region
  repository_id = var.artifact_registry_repo_id
  format        = "DOCKER"
  description   = "InvestLogix container images for Cloud Run Service / Jobs"

  lifecycle {
    # 誤 destroy で過去イメージごと消えるのを防止。意図的に削除する際は一旦この行を外す。
    prevent_destroy = true
  }
}
