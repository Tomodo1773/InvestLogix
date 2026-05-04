resource "google_cloud_run_v2_job" "jobs" {
  for_each = local.jobs

  name                = each.key
  location            = var.region
  deletion_protection = false

  template {
    task_count = 1

    template {
      service_account = google_service_account.jobs_runtime.email
      timeout         = "1800s"
      max_retries     = 1

      containers {
        image   = var.image_uri
        command = ["python"]
        args    = ["-m", each.value]

        resources {
          limits = {
            cpu    = "1"
            memory = "512Mi"
          }
        }

        env {
          name  = "DB_USER"
          value = var.db_user
        }
        env {
          name  = "DB_HOST"
          value = var.db_host
        }
        env {
          name  = "DB_PORT"
          value = var.db_port
        }
        env {
          name  = "DB_NAME"
          value = var.db_name
        }

        dynamic "env" {
          for_each = local.jobs_secrets
          content {
            name = env.value
            value_source {
              secret_key_ref {
                secret  = data.google_secret_manager_secret.all[env.value].secret_id
                version = "latest"
              }
            }
          }
        }
      }
    }
  }

  lifecycle {
    # Cloud Build 自動デプロイ後に scripts/update-cloud-run-jobs.sh が image を更新するため
    # Terraform 側は image とラベルを無視する。
    ignore_changes = [
      template[0].template[0].containers[0].image,
      template[0].labels,
      labels,
      client,
      client_version,
    ]
  }
}

# Scheduler が Job を起動するための invoker 権限（各 Job に個別付与）
resource "google_cloud_run_v2_job_iam_member" "scheduler_invoker" {
  for_each = local.jobs

  project  = google_cloud_run_v2_job.jobs[each.key].project
  location = google_cloud_run_v2_job.jobs[each.key].location
  name     = google_cloud_run_v2_job.jobs[each.key].name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.jobs_invoker.email}"
}
