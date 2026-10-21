// Finance production data platform resources.
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
  name                        = "${var.project_id}-finance-landing-prod"
  location                    = var.region
  uniform_bucket_level_access = true
  versioning { enabled = true }
  labels = { application = "finance", environment = "prod" }
}

resource "google_bigquery_dataset" "raw" {
  dataset_id                 = "finance_raw_prod"
  location                   = var.region
  delete_contents_on_destroy = false
  labels = { application = "finance", environment = "prod", layer = "raw" }
}

resource "google_bigquery_dataset" "core" {
  dataset_id                 = "finance_core_prod"
  location                   = var.region
  delete_contents_on_destroy = false
  labels = { application = "finance", environment = "prod", layer = "core" }
}
