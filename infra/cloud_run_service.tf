resource "google_cloud_run_v2_service" "api" {
  name                = var.service_name
  location            = var.region
  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = false

  # *.run.app のデフォルト URL。Cloudflare Worker の API_ORIGIN が
  # このURLを指しているため無効化してはいけない。カスタムドメインは
  # 同一ゾーンのためWorkerから fetch するとリダイレクトループになる。
  #
  # 直叩きは URL を隠すことでは守らない。API 側が全リクエストで Cloudflare Access の
  # 署名済み JWT を検証するため、Cloudflare を経由しないリクエストは 401 になる。
  default_uri_disabled = false

  # IAM チェックをスキップして認証不要で公開する。
  invoker_iam_disabled = true

  template {
    service_account                  = google_service_account.api_runtime.email
    timeout                          = "300s"
    max_instance_request_concurrency = 80

    scaling {
      max_instance_count = 20
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

      # Cloudflare Access の JWT 検証設定。秘密ではないが環境ごとに変わるため variable で注入する。
      # Cloud Run は *.run.app で直接叩けるので、この検証だけが未認証アクセスの防波堤になる。
      env {
        name  = "CF_ACCESS_TEAM_DOMAIN"
        value = var.cf_access_team_domain
      }
      env {
        name  = "CF_ACCESS_AUD"
        value = var.cf_access_aud
      }

      dynamic "env" {
        for_each = local.service_secrets
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

  # Secret Manager の IAM 伝播待ち（eventual consistency）の前に新リビジョンが起動して
  # secretAccessor 権限不足で失敗するのを防ぐ。
  depends_on = [google_secret_manager_secret_iam_member.api_runtime]

  lifecycle {
    # Cloud Build 自動デプロイが image とラベルを更新するため、OpenTofu は構造のみ管理する。
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
