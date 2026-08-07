resource "google_cloud_run_v2_service" "mcp" {
  name                = var.mcp_service_name
  location            = var.region
  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = false

  # Workerから*.run.appへ転送する。直アクセスはMCP側のAccess JWT検証で拒否する。
  default_uri_disabled = false
  invoker_iam_disabled = true

  template {
    service_account                  = google_service_account.mcp_runtime.email
    timeout                          = "300s"
    max_instance_request_concurrency = 80

    scaling {
      max_instance_count = 5
    }

    containers {
      image = var.image_uri
      ports {
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = "1000m"
          memory = "512Mi"
        }
        cpu_idle          = true
        startup_cpu_boost = true
      }

      env {
        name  = "APP_MODULE"
        value = "stock.mcp.app:app"
      }
      env {
        name  = "ENVIRONMENT"
        value = "production"
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
      env {
        name  = "CF_ACCESS_TEAM_DOMAIN"
        value = var.cf_access_team_domain
      }
      env {
        name  = "CF_ACCESS_AUD"
        value = var.cf_access_mcp_aud
      }

      dynamic "env" {
        for_each = local.mcp_secrets
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

      startup_probe {
        failure_threshold = 1
        period_seconds    = 240
        timeout_seconds   = 240
        tcp_socket {
          port = 8080
        }
      }
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  depends_on = [google_secret_manager_secret_iam_member.mcp_runtime]

  lifecycle {
    ignore_changes = [
      template[0].containers[0].image,
      template[0].labels,
      template[0].revision,
      labels,
      client,
      client_version,
    ]
  }
}
