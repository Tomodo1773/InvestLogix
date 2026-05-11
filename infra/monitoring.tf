# Cloud Monitoring: recalc-holdings ジョブの失敗を検知して管理者にメール通知する。
# ジョブは失敗銘柄が1件でもあれば exit 1 で終了するため、Cloud Run Jobs の
# completed_execution_count{result="failed"} を監視すれば検知できる。

resource "google_monitoring_notification_channel" "dev_email" {
  display_name = "InvestLogix dev email"
  type         = "email"
  labels = {
    email_address = var.alert_email
  }
}

resource "google_monitoring_alert_policy" "recalc_holdings_failed" {
  display_name = "recalc_holdings job failed"
  combiner     = "OR"

  notification_channels = [google_monitoring_notification_channel.dev_email.id]

  conditions {
    display_name = "recalc-holdings completed_execution_count result=failed > 0"
    condition_threshold {
      filter = join(" AND ", [
        "resource.type = \"cloud_run_job\"",
        "resource.labels.job_name = \"recalc-holdings\"",
        "metric.type = \"run.googleapis.com/job/completed_execution_count\"",
        "metric.labels.result = \"failed\"",
      ])
      comparison      = "COMPARISON_GT"
      threshold_value = 0
      duration        = "0s"
      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_SUM"
      }
    }
  }

  alert_strategy {
    auto_close = "604800s" # 7日
  }
}
