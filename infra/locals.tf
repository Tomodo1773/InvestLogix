locals {
  # Cloud Run Jobs 一覧。
  # キーが Cloud Run Job 名、値が Python モジュールパス（python -m <module> で起動）。
  # ジョブを増やすときはここに 1 行追加し、schedules にも追加する。
  jobs = {
    "recalc-holdings"           = "stock.jobs.recalc_holdings"
    "update-and-notify"         = "stock.jobs.update_and_notify"
    "notify-weekly-performance" = "stock.jobs.notify_weekly_performance"
  }

  # Cloud Scheduler の cron 式 (Asia/Tokyo)。
  schedules = {
    "recalc-holdings"           = "0 7 * * *"
    "update-and-notify"         = "30 7 * * 6"
    "notify-weekly-performance" = "0 8 * * 6"
  }

  # Service / Jobs 共通の Secret Manager シークレット名。
  # Service と Jobs で参照するシークレットは部分的に違うので、それぞれ定数化する。
  service_secrets = [
    "DB_PASSWORD",
    "JWT_SECRET_KEY",
    "JQUANTS_API_KEY",
    "ALPHAVANTAGE_API_KEY",
    "LINE_CHANNEL_ACCESS_TOKEN",
    "OPENAI_API_KEY",
  ]

  jobs_secrets = [
    "DB_PASSWORD",
    "LINE_CHANNEL_ACCESS_TOKEN",
    "JQUANTS_API_KEY",
    "ALPHAVANTAGE_API_KEY",
    "OPENAI_API_KEY",
  ]

  all_secrets = toset(concat(local.service_secrets, local.jobs_secrets))

  # CD 用リソースの ID。環境ごとに変える必要がないため variable ではなく local。
  artifact_registry_image_name = "investlogix/investlogix-api"
  deployer_sa_id               = "investlogix-deployer"
  wif_pool_id                  = "github-actions-pool"
  wif_provider_id              = "github-actions-provider"

  image_base = "${var.region}-docker.pkg.dev/${var.project_id}/${var.artifact_registry_repo_id}/${local.artifact_registry_image_name}"
}
