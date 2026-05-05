output "service_uri" {
  value     = google_cloud_run_v2_service.api.uri
  sensitive = true
}

output "service_runtime_sa_email" {
  value = google_service_account.api_runtime.email
}

output "jobs_runtime_sa_email" {
  value = google_service_account.jobs_runtime.email
}

output "jobs_invoker_sa_email" {
  value = google_service_account.jobs_invoker.email
}

# CD ワークフロー (api-cd.yml) で使う値。tofu apply 後に GitHub Actions の Variables へ手動コピーする。
# (sensitive=true は state や stdout に project_id 等が混じるのを抑制するため。秘密ではないが公開リポ方針に合わせる。)

output "wif_provider" {
  description = "GitHub Actions で google-github-actions/auth に渡す provider のフルパス。"
  value       = google_iam_workload_identity_pool_provider.github.name
  sensitive   = true
}

output "deployer_sa_email" {
  description = "GitHub Actions が成り代わる deployer SA のメール。"
  value       = google_service_account.deployer.email
  sensitive   = true
}

output "image_base" {
  description = "ワークフローが docker push / Cloud Run deploy で使うイメージ URI のプレフィックス。"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${var.artifact_registry_repo_id}/${var.artifact_registry_image_name}"
  sensitive   = true
}
