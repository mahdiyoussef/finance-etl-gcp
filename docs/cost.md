# Cost controls

## Cost model

The main cost drivers are:

1. BigQuery bytes scanned by unfiltered queries.
2. Dataflow worker duration.
3. Composer environment uptime.
4. GCS storage and network movement.
5. Monitoring/logging volume.

The local pipeline has no GCP runtime cost. The complete public dataset is
stored locally and excluded from Git.

For GCP deployment:

- Store the source archive in one regional GCS bucket.
- Load only required columns into partitioned BigQuery tables.
- Require partition filters on fact tables.
- Use batch Dataflow for historical ingestion, not always-on streaming.
- Run Composer only for scheduled demonstrations or use an existing Composer
  environment.
- Configure budget alerts before deploying.
- The dev Terraform budget defaults to USD 50/month and has 50%, 80%, and
  100% thresholds. Provide a billing account and notification channel IDs
  before applying it.

## Cost-safe operating pattern

- Keep the downloaded dataset local during development.
- Use BigQuery Sandbox where it meets the experiment requirements.
- Load a bounded date range for development.
- Require partition filters on invoice and event tables.
- Use one regional deployment for storage and compute.
- Stop or delete temporary Dataflow jobs after demonstrations.
- Avoid leaving Composer running solely for a portfolio screenshot.
- Review billing export data after each cloud run.

Record measured bytes scanned and job duration in the project results section;
do not claim percentage savings without a before/after benchmark.
