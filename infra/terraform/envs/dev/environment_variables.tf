variable "project_id" {
  type        = string
  description = "GCP project ID."
}

variable "region" {
  type    = string
  default = "us-central1"
}

variable "billing_account_id" {
  type        = string
  description = "Billing account ID used for budget alerts."
}

variable "monthly_budget_usd" {
  type    = number
  default = 50
}

variable "notification_channel_ids" {
  type    = list(string)
  default = []
}
