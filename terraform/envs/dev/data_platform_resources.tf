// FinPulse development data platform resources.
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
  name                        = "${var.project_id}-finpulse-landing"
  location                    = var.region
  uniform_bucket_level_access = true
  labels                      = { application = "finpulse", environment = "dev" }
  lifecycle_rule {
    condition { age = 30 }
    action { type = "Delete" }
  }
}

resource "google_bigquery_dataset" "raw" {
  dataset_id                 = "finpulse_raw"
  location                   = var.region
  delete_contents_on_destroy = true
  labels                      = { application = "finpulse", layer = "raw" }
}

resource "google_bigquery_dataset" "core" {
  dataset_id                 = "finpulse_core"
  location                   = var.region
  delete_contents_on_destroy = true
  labels                      = { application = "finpulse", layer = "core" }
}

resource "google_pubsub_topic" "ticket_events" {
  name = "finpulse-ticket-events"
  labels = { application = "finpulse", environment = "dev" }
}

resource "google_pubsub_topic" "ticket_dead_letter" {
  name = "finpulse-ticket-events-dlq"
}

resource "google_pubsub_subscription" "ticket_events" {
  name  = "finpulse-ticket-events-sub"
  topic = google_pubsub_topic.ticket_events.name
  ack_deadline_seconds = 30
  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.ticket_dead_letter.id
    max_delivery_attempts = 5
  }
}

resource "google_pubsub_subscription" "ticket_dead_letter" {
  name  = "finpulse-ticket-events-dlq-sub"
  topic = google_pubsub_topic.ticket_dead_letter.name
  message_retention_duration = "604800s"
}
