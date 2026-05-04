resource "google_cloud_scheduler_job" "jobs" {
  for_each = local.schedules

  name      = "${each.key}-scheduler"
  region    = var.region
  schedule  = each.value
  time_zone = "Asia/Tokyo"

  retry_config {
    retry_count = 0
  }

  http_target {
    http_method = "POST"
    # Cloud Run Jobs の :run エンドポイントは run.googleapis.com (Google API) のため OAuth トークン認証。
    uri = "https://${var.region}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${var.project_id}/jobs/${each.key}:run"

    oauth_token {
      service_account_email = google_service_account.jobs_invoker.email
    }
  }

  depends_on = [
    google_cloud_run_v2_job_iam_member.scheduler_invoker,
  ]
}
