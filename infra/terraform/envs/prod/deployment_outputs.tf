output "landing_bucket" {
  value = google_storage_bucket.landing.name
}

output "raw_dataset" {
  value = google_bigquery_dataset.raw.dataset_id
}
