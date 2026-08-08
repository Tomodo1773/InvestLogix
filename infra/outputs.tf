output "service_uri" {
  value     = google_cloud_run_v2_service.api.uri
  sensitive = true
}

output "service_runtime_sa_email" {
  value = google_service_account.api_runtime.email
}

output "mcp_service_uri" {
  value     = google_cloud_run_v2_service.mcp.uri
  sensitive = true
}

output "mcp_runtime_sa_email" {
  value = google_service_account.mcp_runtime.email
}

output "jobs_runtime_sa_email" {
  value = google_service_account.jobs_runtime.email
}

output "jobs_invoker_sa_email" {
  value = google_service_account.jobs_invoker.email
}

# api-cd.yml が読む値。tofu apply 後に GitHub Actions の Variables へ手動コピーする。

output "wif_provider" {
  value     = google_iam_workload_identity_pool_provider.github.name
  sensitive = true
}

output "deployer_sa_email" {
  value     = google_service_account.deployer.email
  sensitive = true
}

output "image_base" {
  value = local.image_base
}
