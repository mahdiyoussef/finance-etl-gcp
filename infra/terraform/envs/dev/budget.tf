// Development budget guardrail for the Finance ETL platform.
resource "google_billing_budget" "finance" {
  billing_account = var.billing_account_id
  display_name    = "Finance dev budget"
  amount {
    specified_amount {
      currency_code = "USD"
      units         = var.monthly_budget_usd
    }
  }
  threshold_rules { threshold_percent = 0.5 }
  threshold_rules { threshold_percent = 0.8 }
  threshold_rules { threshold_percent = 1.0 }
  all_updates_rule {
    monitoring_notification_channels = var.notification_channel_ids
  }
}
