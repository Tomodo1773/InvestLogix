resource "google_artifact_registry_repository" "api" {
  location      = var.region
  repository_id = var.artifact_registry_repo_id
  format        = "DOCKER"
  description   = "InvestLogix container images for Cloud Run Service / Jobs"

  lifecycle {
    prevent_destroy = true
  }
}
