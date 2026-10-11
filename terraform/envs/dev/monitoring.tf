// Alert when ingestion quality metrics report quarantined rows.
resource "google_monitoring_alert_policy" "quarantine_rate" {
  display_name = "FinPulse quarantine rate"
  combiner     = "OR"
  conditions {
    display_name = "Quarantined rows reported"
    condition_threshold {
      filter          = "metric.type=\"logging.googleapis.com/user/finpulse_quarantine_rows\""
      comparison      = "COMPARISON_GT"
      threshold_value = 0
      duration        = "300s"
      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_SUM"
      }
    }
  }
  alert_strategy { auto_close = "1800s" }
  documentation {
    content = "Inspect the quarantine table and source file before rerunning marts."
  }
}
