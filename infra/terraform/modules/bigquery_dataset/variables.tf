variable "dataset_id" {
  type        = string
  description = "BigQuery dataset identifier."
}

variable "location" {
  type        = string
  description = "GCP region for the dataset."
  default     = "US"
}

variable "delete_contents_on_destroy" {
  type        = bool
  description = "Whether to delete dataset contents on terraform destroy."
  default     = false
}

variable "labels" {
  type        = map(string)
  description = "Labels to apply to the dataset."
  default     = {}
}

