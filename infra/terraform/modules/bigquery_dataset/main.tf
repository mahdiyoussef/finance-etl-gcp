// Reusable BigQuery dataset module with standard labels and partition protection.
resource "google_bigquery_dataset" "this" {
  dataset_id                 = var.dataset_id
  location                   = var.location
  delete_contents_on_destroy = var.delete_contents_on_destroy
  labels                     = var.labels
}

