// Least-privilege service account bindings for development ingestion.
resource "google_service_account" "batch" {
  account_id   = "finpulse-batch"
  display_name = "FinPulse batch ingestion"
}

resource "google_storage_bucket_iam_member" "batch_landing_writer" {
  bucket = google_storage_bucket.landing.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.batch.email}"
}

resource "google_bigquery_dataset_iam_member" "batch_raw_editor" {
  dataset_id = google_bigquery_dataset.raw.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.batch.email}"
}

resource "google_project_iam_member" "batch_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.batch.email}"
}
