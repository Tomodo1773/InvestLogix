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
