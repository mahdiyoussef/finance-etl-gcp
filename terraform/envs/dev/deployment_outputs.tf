output "landing_bucket" {
  value = google_storage_bucket.landing.name
}

output "raw_dataset" {
  value = google_bigquery_dataset.raw.dataset_id
}

output "batch_service_account" {
  value = google_service_account.batch.email
}
