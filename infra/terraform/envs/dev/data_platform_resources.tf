// Finance development data platform resources.
terraform {
  required_version = ">= 1.6.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_storage_bucket" "landing" {
  name                        = "${var.project_id}-finance-landing"
  location                    = var.region
  uniform_bucket_level_access = true
  labels                      = { application = "finance", environment = "dev" }
  lifecycle_rule {
    condition { age = 30 }
    action { type = "Delete" }
  }
}

resource "google_bigquery_dataset" "raw" {
  dataset_id                 = "finance_raw"
  location                   = var.region
  delete_contents_on_destroy = true
  labels                      = { application = "finance", layer = "raw" }
}

resource "google_bigquery_dataset" "core" {
  dataset_id                 = "finance_core"
  location                   = var.region
  delete_contents_on_destroy = true
  labels                      = { application = "finance", layer = "core" }
}

resource "google_pubsub_topic" "ticket_events" {
  name = "finance-ticket-events"
  labels = { application = "finance", environment = "dev" }
}

resource "google_pubsub_topic" "ticket_dead_letter" {
  name = "finance-ticket-events-dlq"
}

resource "google_pubsub_subscription" "ticket_events" {
  name  = "finance-ticket-events-sub"
  topic = google_pubsub_topic.ticket_events.name
  ack_deadline_seconds = 30
  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.ticket_dead_letter.id
    max_delivery_attempts = 5
  }
}

resource "google_pubsub_subscription" "ticket_dead_letter" {
  name  = "finance-ticket-events-dlq-sub"
  topic = google_pubsub_topic.ticket_dead_letter.name
  message_retention_duration = "604800s"
}
