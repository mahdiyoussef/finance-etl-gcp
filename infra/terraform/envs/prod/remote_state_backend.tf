terraform {
  backend "gcs" {
    bucket = "REPLACE_WITH_PRODUCTION_STATE_BUCKET"
    prefix = "finance/prod"
  }
}
