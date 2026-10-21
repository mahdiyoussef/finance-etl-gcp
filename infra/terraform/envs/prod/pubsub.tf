// Production ticket-event topics and retryable subscriptions.
resource "google_pubsub_topic" "ticket_events" {
  name   = "finance-ticket-events-prod"
  labels = { application = "finance", environment = "prod" }
}

resource "google_pubsub_topic" "ticket_dead_letter" {
  name = "finance-ticket-events-dlq-prod"
}

resource "google_pubsub_subscription" "ticket_events" {
  name  = "finance-ticket-events-prod-sub"
  topic = google_pubsub_topic.ticket_events.name
  ack_deadline_seconds = 30
  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.ticket_dead_letter.id
    max_delivery_attempts = 5
  }
}
